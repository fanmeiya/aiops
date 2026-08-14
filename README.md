# WaLiSSH Python Server

Python 3/FastAPI drop-in backend for WaLiSSH. The runtime uses Claude Agent SDK, an in-process remote `executeCommand` MCP tool, AsyncSSH persistent PTYs/SFTP, SQLAlchemy, MySQL and Pydantic.

## Start

```bash
cp .env.example .env
# Set WALISSH_DATABASE_URL, WALISSH_SECRET_KEY and ANTHROPIC_API_KEY
python -m pip install -e '.[test]'
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

The service reads the existing `walissh` MySQL schema and does not rename or migrate its columns. `chat_stream` intentionally returns newline-delimited JSON objects, matching the previous server; it is not `data:`-framed SSE.

## Identity and execution boundaries

Application chat sessions, Claude sessions, terminal sessions, connections and users remain distinct. Agent commands can only execute through the `executeCommand` MCP tool against the bound AsyncSSH PTY. No local Bash tool is enabled.

See `FEATURE_INVENTORY.md`, `IMPLEMENTATION_MAPPING.md`, `API_COMPATIBILITY_MATRIX.md`, and `COMPATIBILITY_QUIRKS.md` for the source audit and compatibility decisions.

Production acceptance requirements and the distinction between automation-capable and fully certified are documented in `AUTOMATION_READINESS.md`.
