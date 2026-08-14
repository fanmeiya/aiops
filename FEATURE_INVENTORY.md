# WaLiSSH Feature Inventory

## HTTP API

The FastAPI service exposes Agent configuration/session/chat endpoints, SSH connection lifecycle endpoints, terminal endpoints, file endpoints, and Agent-to-terminal binding endpoints. Every business response uses `{code, info, data}` and request fields remain camelCase for frontend compatibility.

## Agent runtime

The LangGraph runtime coordinates DeepSeek model calls, the bounded tool loop, graph state and termination. The application adapter provides `text`, `tool_call`, `tool_result`, `round_end`, `done`, and `error` NDJSON events plus step/tool limits, idle timeout, remote-tool permissions and result statistics.

## Enterprise knowledge RAG

Tenant-scoped operational documents are split by Markdown sections and bounded overlapping windows. Retrieval applies tenant, role, service and environment filters before hybrid lexical/vector scoring. Embeddings are optional through an OpenAI-compatible provider; lexical retrieval remains available for local operation. LangGraph retrieves knowledge before model inference and returns document, section, version and URI citations in stream and completion events.

## Remote automation

AsyncSSH owns live SSH connections. Each terminal is a persistent interactive PTY with independent browser and Agent drain buffers. The only Agent execution tool, `executeCommand`, runs against the bound remote terminal; no local command tool is enabled. SFTP supports directory trees, text/binary reads, chunking, create/rename/delete/save, multipart upload and binary download.

## Context and intent

Application memory remains independent of graph execution state. Durable chat history, milestones, terminal state, task context and tool summaries feed the prompt builder. Sliding-window, priority and hybrid reducers enforce the context budget. Intent classification uses deterministic rules, recent-intent weighting, entity extraction and a DeepSeek fallback.

## Persistence and configuration

SQLAlchemy maps chat, SSH and enterprise knowledge document/chunk/query-log tables. Credentials use AES-256-GCM and configuration/secrets come from environment variables. The service is packaged with `pyproject.toml`, Uvicorn, Docker and Compose.
