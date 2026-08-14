# Python Implementation Map

| Responsibility | Python implementation |
|---|---|
| HTTP application and Agent routes | `app/main.py` |
| SSH connection, terminal, file and binding routes | `app/api.py` |
| CamelCase request models and response envelope | `app/schemas.py` |
| Claude Agent SDK loop and compatibility events | `app/agent/runtime.py` |
| Deterministic remote command policy | `app/agent/permissions.py` |
| Context providers, reducers and prompt composition | `app/agent/context.py` |
| Rule/Claude intent classification | `app/agent/intent.py` |
| User/chat/Claude/terminal/connection mapping | `app/agent/state.py` |
| Persistent interactive SSH PTY and SFTP | `app/ssh.py` |
| Durable chat and milestone repository | `app/memory.py` |
| Existing MySQL table mappings | `app/persistence.py` |
| AES-256-GCM credential handling | `app/security.py` |
| Environment-driven settings | `app/config.py` |
| Agent behavior definition and skills | `app/agent/ssh-agent.yml`, `app/agent/skills/` |
| Deployment | `Dockerfile`, `docs/dev-ops/docker-compose-app.yml` |
| Compatibility and readiness verification | `tests/`, `API_COMPATIBILITY_MATRIX.md`, `AUTOMATION_READINESS.md` |
