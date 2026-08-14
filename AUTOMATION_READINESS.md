# Automation Readiness Audit

The service can perform automated operations when all three external systems are configured: MySQL, Anthropic/Claude Agent SDK, and a reachable SSH server. This audit does not claim live end-to-end certification without those systems.

## Verified in code

- Agent Bash is disabled; the only enabled execution tool is the in-process `executeCommand` MCP tool.
- `executeCommand` rejects missing terminal bindings and runs through the persistent remote AsyncSSH PTY.
- Browser terminal output and Agent capture observe the same PTY through independent drain buffers.
- Agent execution is serialized per chat session, bounded by 50 turns, 200 tool calls, and a 180-second event-idle timeout.
- Destructive commands require explicit confirmation in the current user message.
- Existing application history and milestones are restored from MySQL and injected if a Claude session cannot resume.
- SFTP clients are cached per connection and closed on disconnect; explicit privileged file operations use non-interactive remote sudo.
- Streaming remains newline-delimited JSON rather than SSE framing.

## External acceptance gates

Before production cutover, run the compatibility suite with dependencies installed, then run live integration fixtures against:

1. MySQL initialized from `docs/dev-ops/mysql/sql/walissh.sql`, including pre-existing encrypted credentials and history.
2. A disposable SSH host supporting password and private-key authentication, PTY resize, SFTP, and passwordless sudo.
3. A real Claude Agent SDK session which diagnoses a fault, performs multiple remote tool calls, resumes the conversation, and emits all compatibility events.
4. The existing frontend consuming `/api/v1/chat_stream` without modifications.

Until these gates pass, the implementation is automation-capable but not production-certified.
