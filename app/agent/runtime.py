import json, re, uuid
from pathlib import Path
from typing import AsyncIterator
from app.ssh import ssh_manager

PROMPT_FILE = Path(__file__).with_name('ssh-agent.yml')
# Preserve the complete Java prompt byte-for-byte as the initial migration source.
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding='utf-8').split('instruction: |', 1)[1]

# Deterministic backstop; prompt instructions alone are not a security boundary.
DESTRUCTIVE = [
    re.compile(r'(^|[;&|]\s*)rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)'),
    re.compile(r'\bmkfs(?:\.|\s)'), re.compile(r'\bdd\s+[^\n]*\bof=/dev/'),
    re.compile(r'\b(?:DROP\s+(?:DATABASE|TABLE)|TRUNCATE\s+TABLE)\b', re.I),
    re.compile(r'\b(?:shutdown|reboot|poweroff)\b'),
]


def check_permission(command: str) -> None:
    if any(p.search(command) for p in DESTRUCTIVE):
        raise PermissionError('高风险命令需要用户明确确认，已阻止执行')


async def execute_command(command: str, terminal_session_id: str) -> str:
    check_permission(command)
    return await ssh_manager.execute(terminal_session_id, command)


class AgentRuntime:
    """Claude Agent SDK adapter which retains Java counters and event vocabulary."""
    max_steps = 50; max_tool_calls = 200; max_tool_calls_per_round = 10

    async def stream(self, request, terminal_id: str | None) -> AsyncIterator[dict]:
        text = ''; calls=[]; results=[]; steps=0; error=None; stop='completed'
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, create_sdk_mcp_server, tool

            @tool("executeCommand", "在用户绑定的远程 SSH 终端中执行命令", {"command": str})
            async def remote_execute(args):
                try:
                    output = await execute_command(args["command"], terminal_id or "")
                    return {"content": [{"type": "text", "text": output}]}
                except Exception as exc:
                    return {"content": [{"type": "text", "text": str(exc)}], "is_error": True}

            server = create_sdk_mcp_server(name="ssh", version="1.0.0", tools=[remote_execute])
            options = ClaudeAgentOptions(system_prompt=SYSTEM_PROMPT,
                                         mcp_servers={"ssh": server},
                                         allowed_tools=["mcp__ssh__executeCommand"])
            async with ClaudeSDKClient(options=options) as client:
                await client.query(request.message or '')
                async for message in client.receive_response():
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
                    steps += 1
                    yield {'event':'round_end','content':None,'toolCallId':None,'toolName':None,'status':None,'fullText':None,
                           'stepInfo':{'currentStep':steps,'maxSteps':self.max_steps,'shouldContinue':steps<self.max_steps,'totalToolCalls':len(calls)}}
                    if steps>=self.max_steps: stop='max_steps'; break
        except Exception as exc:
            error=str(exc); stop='error'
            yield {'event':'error','content':error,'toolCallId':None,'toolName':None,'status':'error','fullText':text,'stepInfo':None}
        result={'content':text,'totalSteps':steps,'totalToolCalls':len(calls),'maxStepsReached':stop=='max_steps',
                'userStopped':False,'idleTimeout':False,'stopReason':stop,'toolCalls':calls,'toolResults':results,'error':error}
        yield {'event':'done','content':json.dumps(result,ensure_ascii=False),'toolCallId':None,'toolName':None,'status':'success' if not error else 'error','fullText':text,'stepInfo':None}

runtime=AgentRuntime()
