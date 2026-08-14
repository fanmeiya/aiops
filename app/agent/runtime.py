"""LangGraph ReAct runtime backed by DeepSeek's OpenAI-compatible API."""
import asyncio
import json
import uuid
from pathlib import Path
from typing import AsyncIterator, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agent.context import tool_results
from app.agent.model import deepseek_client
from app.agent.permissions import check_permission
from app.config import settings
from app.ssh import ssh_manager

PROMPT_FILE = Path(__file__).with_name("ssh-agent.yml")
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8").split("instruction: |", 1)[1]
EXECUTE_TOOL = {
    "type": "function",
    "function": {
        "name": "executeCommand",
        "description": "在用户绑定的远程 SSH 终端中执行命令",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
            "additionalProperties": False,
        },
    },
}


class GraphState(TypedDict):
    messages: list[dict]
    session_id: str
    terminal_id: str
    user_message: str
    steps: int
    tool_count: int
    calls: list[dict]
    results: list[dict]
    events: list[dict]
    stop_reason: str
    error: str | None


async def execute_command(command: str, terminal_session_id: str, user_message: str = "") -> str:
    if not terminal_session_id:
        raise RuntimeError("未绑定 SSH 终端会话。请先打开并绑定终端。")
    check_permission(command, user_message)
    return await ssh_manager.execute(terminal_session_id, command)


class AgentRuntime:
    """Runs a bounded model/tool graph and preserves the public NDJSON events."""

    max_tool_calls_per_round = 10

    def __init__(self):
        self.max_steps = settings.agent_max_steps
        self.max_tool_calls = settings.agent_max_tool_calls
        self._session_locks: dict[str, asyncio.Lock] = {}
        graph = StateGraph(GraphState)
        graph.add_node("model", self._model)
        graph.add_node("tools", self._tools)
        graph.add_edge(START, "model")
        graph.add_conditional_edges("model", self._route, {"tools": "tools", "end": END})
        graph.add_edge("tools", "model")
        self.graph = graph.compile()

    async def _model(self, state: GraphState) -> dict:
        if state["steps"] >= self.max_steps:
            return {"stop_reason": "max_steps", "events": []}
        response = await deepseek_client().chat.completions.create(
            model=settings.deepseek_model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, *state["messages"]],
            tools=[EXECUTE_TOOL],
            tool_choice="auto",
        )
        message = response.choices[0].message
        content = message.content or ""
        serialized = message.model_dump(exclude_none=True)
        events: list[dict] = []
        calls = list(state["calls"])
        if content:
            events.append(self._event("text", content=content, fullText=content))
        for call in message.tool_calls or []:
            arguments = self._arguments(call.function.arguments)
            record = {"id": call.id, "name": call.function.name, "arguments": arguments}
            calls.append(record)
            events.append(self._event("tool_call", content=json.dumps(arguments, ensure_ascii=False),
                                      toolCallId=call.id, toolName=call.function.name, status="running"))
        step = state["steps"] + 1
        events.append(self._event("round_end", stepInfo={
            "currentStep": step,
            "maxSteps": self.max_steps,
            "shouldContinue": step < self.max_steps,
            "totalToolCalls": len(calls),
        }))
        stop = "completed" if not message.tool_calls else ""
        if len(calls) > self.max_tool_calls:
            stop = "max_tool_calls"
        return {"messages": [*state["messages"], serialized], "steps": step, "calls": calls,
                "events": events, "stop_reason": stop}

    async def _tools(self, state: GraphState) -> dict:
        assistant = state["messages"][-1]
        messages = list(state["messages"])
        results = list(state["results"])
        events: list[dict] = []
        executed = 0
        for call in assistant.get("tool_calls", []):
            if executed >= self.max_tool_calls_per_round or state["tool_count"] + executed >= self.max_tool_calls:
                output, status = "已达到最大工具调用次数", "error"
            elif call["function"]["name"] != "executeCommand":
                output, status = "不支持的工具", "error"
            else:
                try:
                    args = self._arguments(call["function"].get("arguments", "{}"))
                    output = await execute_command(args.get("command", ""), state["terminal_id"], state["user_message"])
                    tool_results.push(state["session_id"], "executeCommand", output)
                    status = "success"
                except Exception as exc:
                    output, status = str(exc), "error"
            executed += 1
            result = {"toolCallId": call["id"], "content": output, "status": status}
            results.append(result)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": output})
            events.append(self._event("tool_result", content=output, toolCallId=call["id"], status=status))
        return {"messages": messages, "results": results, "events": events,
                "tool_count": state["tool_count"] + executed}

    def _route(self, state: GraphState) -> str:
        if state["stop_reason"] or state["steps"] >= self.max_steps or state["tool_count"] >= self.max_tool_calls:
            return "end"
        return "tools" if state["messages"][-1].get("tool_calls") else "end"

    async def stream(self, request, terminal_id: str | None, enriched_message: str | None = None) -> AsyncIterator[dict]:
        lock = self._session_locks.setdefault(request.sessionId, asyncio.Lock())
        async with lock:
            text = ""
            state: GraphState = {
                "messages": [{"role": "user", "content": enriched_message or request.message or ""}],
                "session_id": request.sessionId,
                "terminal_id": terminal_id or "",
                "user_message": request.message or "",
                "steps": 0, "tool_count": 0, "calls": [], "results": [], "events": [],
                "stop_reason": "", "error": None,
            }
            final = state
            try:
                async with asyncio.timeout(180):
                    async for update in self.graph.astream(state, stream_mode="updates"):
                        values = next(iter(update.values()))
                        final = {**final, **values}
                        for event in values.get("events", []):
                            if event["event"] == "text":
                                text += event["content"] or ""
                                event["fullText"] = text
                            yield event
            except TimeoutError:
                final = {**final, "error": "Agent 180 秒无事件，已停止", "stop_reason": "idle_timeout"}
                yield self._event("error", content=final["error"], status="error", fullText=text)
            except Exception as exc:
                final = {**final, "error": str(exc), "stop_reason": "error"}
                yield self._event("error", content=str(exc), status="error", fullText=text)
            stop = final.get("stop_reason") or "completed"
            result = {"content": text, "totalSteps": final.get("steps", 0),
                      "totalToolCalls": len(final.get("calls", [])), "maxStepsReached": stop == "max_steps",
                      "userStopped": False, "idleTimeout": stop == "idle_timeout", "stopReason": stop,
                      "toolCalls": final.get("calls", []), "toolResults": final.get("results", []),
                      "error": final.get("error")}
            yield self._event("done", content=json.dumps(result, ensure_ascii=False),
                              status="error" if final.get("error") else "success", fullText=text)

    @staticmethod
    def _arguments(raw) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            value = json.loads(raw or "{}")
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def _event(event: str, **values) -> dict:
        payload = {"event": event, "content": None, "toolCallId": None, "toolName": None,
                   "status": None, "fullText": None, "stepInfo": None}
        payload.update(values)
        return payload


runtime = AgentRuntime()
