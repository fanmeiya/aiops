import asyncio, json, uuid
from pathlib import Path
from typing import AsyncIterator
from app.ssh import ssh_manager
from app.agent.context import tool_results
from app.agent.state import session_registry
from app.agent.permissions import check_permission
from app.config import settings

PROMPT_FILE = Path(__file__).with_name('ssh-agent.yml')
# Load the complete SSH operations policy as the system prompt.
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding='utf-8').split('instruction: |', 1)[1]

async def execute_command(command: str, terminal_session_id: str, user_message: str = "") -> str:
    if not terminal_session_id:
        raise RuntimeError("未绑定 SSH 终端会话。请先打开并绑定终端。")
    check_permission(command, user_message)
    return await ssh_manager.execute(terminal_session_id, command)


class AgentRuntime:
    """Claude Agent SDK adapter for the public ReAct counters and event vocabulary."""
    max_steps = 50; max_tool_calls = 200; max_tool_calls_per_round = 10

    def __init__(self):
        self._session_locks: dict[str, asyncio.Lock] = {}

    async def _idle_bounded(self, messages, timeout=180):
        iterator = messages.__aiter__()
        while True:
            try:
                yield await asyncio.wait_for(iterator.__anext__(), timeout)
            except StopAsyncIteration:
                return

    async def stream(self, request, terminal_id: str | None, enriched_message: str | None = None) -> AsyncIterator[dict]:
        lock = self._session_locks.setdefault(request.sessionId, asyncio.Lock())
        async with lock:
            async for event in self._stream_locked(request, terminal_id, enriched_message):
                yield event

    async def _stream_locked(self, request, terminal_id, enriched_message):
        text = ''; calls=[]; results=[]; steps=0; error=None; stop='completed'; executed=0; round_executed=0; idle_timeout=False
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool

            @tool("executeCommand", "在用户绑定的远程 SSH 终端中执行命令", {"command": str})
            async def remote_execute(args):
                nonlocal executed, round_executed
                try:
                    if executed >= self.max_tool_calls:
                        raise RuntimeError("已达到最大工具调用次数")
                    if round_executed >= self.max_tool_calls_per_round:
                        raise RuntimeError("当前轮次已达到最大工具调用次数")
                    executed += 1; round_executed += 1
                    output = await execute_command(args["command"], terminal_id or "", request.message or "")
                    tool_results.push(request.sessionId, "executeCommand", output)
                    return {"content": [{"type": "text", "text": output}]}
                except Exception as exc:
                    return {"content": [{"type": "text", "text": str(exc)}], "is_error": True}

            server = create_sdk_mcp_server(name="ssh", version="1.0.0", tools=[remote_execute])
            options = ClaudeAgentOptions(system_prompt=SYSTEM_PROMPT,
                                         model=settings.agent_model,
                                         mcp_servers={"ssh": server},
                                         allowed_tools=["mcp__ssh__executeCommand"],
                                         max_turns=self.max_steps)
            mapping=session_registry.get(request.sessionId)
            if mapping and mapping.claude_session_id:
                options.resume=mapping.claude_session_id
            async with ClaudeSDKClient(options=options) as client:
                await client.query(enriched_message or request.message or '')
                async for message in self._idle_bounded(client.receive_response()):
                    sdk_session_id=getattr(message,'session_id',None)
                    if sdk_session_id: session_registry.set_claude(request.sessionId,sdk_session_id)
                    # SDK message shapes evolve; adapt content blocks without leaking SDK wire format.
                    for block in getattr(message, 'content', []) or []:
                        kind = block.__class__.__name__.lower()
                        if 'text' in kind:
                            chunk=getattr(block,'text',''); text += chunk
                            yield {'event':'text','content':chunk,'toolCallId':None,'toolName':None,'status':None,'fullText':text,'stepInfo':None}
                        elif 'tooluse' in kind:
                            if len(calls)>=self.max_tool_calls: stop='max_tool_calls'; break
                            tool_id=getattr(block,'id',str(uuid.uuid4())); name=getattr(block,'name','')
                            args=getattr(block,'input',{}) or {}; calls.append({'id':tool_id,'name':name,'arguments':args})
                            yield {'event':'tool_call','content':json.dumps(args,ensure_ascii=False),'toolCallId':tool_id,'toolName':name,'status':'running','fullText':None,'stepInfo':None}
                        elif 'toolresult' in kind:
                            tool_id=getattr(block,'tool_use_id',None)
                            raw=getattr(block,'content',''); output=raw if isinstance(raw,str) else json.dumps(raw,ensure_ascii=False,default=str)
                            status='error' if getattr(block,'is_error',False) else 'success'
                            results.append({'toolCallId':tool_id,'content':output,'status':status})
                            yield {'event':'tool_result','content':output,'toolCallId':tool_id,'toolName':None,'status':status,'fullText':None,'stepInfo':None}
                    # Only assistant messages represent application reasoning rounds.
                    if message.__class__.__name__.lower().startswith('assistant'):
                        steps += 1
                        # Its tool calls execute after this SDK message is consumed.
                        round_executed = 0
                    else:
                        continue
                    yield {'event':'round_end','content':None,'toolCallId':None,'toolName':None,'status':None,'fullText':None,
                           'stepInfo':{'currentStep':steps,'maxSteps':self.max_steps,'shouldContinue':steps<self.max_steps,'totalToolCalls':len(calls)}}
                    if steps>=self.max_steps: stop='max_steps'; break
        except asyncio.TimeoutError as exc:
            error='Agent 180 秒无事件，已停止'; stop='idle_timeout'; idle_timeout=True
            yield {'event':'error','content':error,'toolCallId':None,'toolName':None,'status':'error','fullText':text,'stepInfo':None}
        except Exception as exc:
            error=str(exc); stop='error'
            yield {'event':'error','content':error,'toolCallId':None,'toolName':None,'status':'error','fullText':text,'stepInfo':None}
        result={'content':text,'totalSteps':steps,'totalToolCalls':len(calls),'maxStepsReached':stop=='max_steps',
                'userStopped':False,'idleTimeout':idle_timeout,'stopReason':stop,'toolCalls':calls,'toolResults':results,'error':error}
        yield {'event':'done','content':json.dumps(result,ensure_ascii=False),'toolCallId':None,'toolName':None,'status':'success' if not error else 'error','fullText':text,'stepInfo':None}

runtime=AgentRuntime()
