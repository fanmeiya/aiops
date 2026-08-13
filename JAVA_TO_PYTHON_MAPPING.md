# Java to Python Mapping

| Java implementation | Responsibility | Python implementation |
|---|---|---|
| Spring controllers + DTOs | public HTTP contract | FastAPI routes in `app/main.py`, `app/api.py`; Pydantic request models |
| `Response<T>` / `ResponseCode` | envelope and business errors | `app.schemas.envelope` and route adapters |
| MyBatis PO/DAO/repositories | existing MySQL storage | async SQLAlchemy models/session in `app/persistence.py` |
| JSch `SshSessionPort` | SSH connection lifecycle | AsyncSSH connections in `app/ssh.py` |
| JSch `TerminalSessionPort` | persistent PTY and dual buffers | `SSHManager`/`Terminal` with one PTY, UI and agent buffers |
| `SshFilePort` | SFTP and downloads | async SFTP routes in `app/api.py` |
| ADK/Spring AI node/runtime graph | LLM/tool loop | `ClaudeSDKClient` adapter in `app/agent/runtime.py` |
| `SshExecuteAdkTool.executeCommand` | bound remote execution | `execute_command` using `SSHManager.execute` only |
| ReAct DTO/emitter | counters and NDJSON protocol | runtime counter/event adapter + `StreamingResponse` |
| Java agent instruction | SSH SRE behavior | verbatim `app/agent/ssh-agent.yml` system prompt source |
| prompt-only safety | confirmation policy | prompt plus deterministic pre-tool command guard |
| chat session/history | durable application memory | `ChatSession`/`ChatMessage`; distinct terminal binding |

Claude session IDs remain runtime-owned; application chat IDs and terminal IDs remain explicit and separate. No schema migration is required by this rewrite.
