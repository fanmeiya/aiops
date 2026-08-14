# Java to Python Mapping

The Java runtime modules were removed after their observable responsibilities were migrated. This table records the behavioral mapping rather than a class-for-class translation.

| Former Java responsibility | Python implementation |
|---|---|
| Spring controllers, DTO binding, `Response<T>` | FastAPI routes in `app/main.py` and `app/api.py`; Pydantic camelCase request schemas and `envelope` |
| Controller exception-to-business-code conversion | Route adapters preserving `0000`, `0001`, `0002`, `E0001` and localized messages |
| MyBatis DAOs, POs and repositories | Async SQLAlchemy schema in `app/persistence.py`; durable repository in `app/memory.py` |
| `chat_message`, `chat_milestone`, `chat_session` | Matching SQLAlchemy tables, history continuation, message counts and milestone persistence |
| `ssh_connection`, config, and session log | Matching SQLAlchemy tables, encrypted credentials and lifecycle logging |
| JSch connection/session ports | AsyncSSH connection lifecycle in `app/ssh.py` |
| JSch interactive `ChannelShell` | Persistent AsyncSSH PTY with browser drain buffer and gated Agent capture buffer |
| SFTP port and sudo-aware file service | Async SFTP tree/content/chunk/mutation/upload/download routes; compatibility exception documented |
| ADK/Spring AI runner/node graph | Claude Agent SDK loop and NDJSON event adapter in `app/agent/runtime.py` |
| `SshExecuteAdkTool.executeCommand` | In-process MCP `executeCommand`, restricted to the bound remote PTY |
| ReAct dynamic state and termination DTO | 50-step/200-call/10-per-round application counters and Java event/result vocabulary |
| Chat/Claude/terminal binding state | Explicit `SessionMapping`/`SessionRegistry` in `app/agent/state.py` |
| Context providers | Terminal/task/milestone/tool-result composition in `app/agent/context.py` |
| Sliding, priority, hybrid reducers | Behavior-preserving reducer implementations in `app/agent/context.py` |
| Rule and LLM intent classifiers/context tracker | Two-layer classifier, 10-turn context and five-minute LRU cache in `app/agent/intent.py` |
| Dynamic prompt builder and prompt service | Environment/command/milestone/tool/task prefix composition in `app/agent/context.py` |
| Milestone tracker | Detection plus durable/in-memory retrieval in `app/memory.py` |
| Java AES-256-GCM encryptor | Compatible IV+ciphertext Base64 format in `app/security.py` |
| Spring/YAML secrets | Pydantic environment settings and `.env.example`; no committed credentials |
| Maven/Spring Boot packaging | `pyproject.toml`, Uvicorn entry point, Dockerfile and Python Compose service |
