from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CreateSession(APIModel): agentId: str | None = None; userId: str | None = None
class ChatRequest(APIModel):
    agentId: str | None = None; userId: str | None = None; sessionId: str | None = None
    message: str | None = None; terminalSessionId: str | None = None
    tenantId: str = "default"; roles: list[str] = Field(default_factory=list); service: str | None = None; environment: str | None = None
class Binding(APIModel): chatSessionId: str | None = None; terminalSessionId: str | None = None
class ConnectionRequest(APIModel):
    connectionId: str | None = None; connectionName: str | None = None; host: str | None = None
    port: int | None = None; username: str | None = None; authType: int | None = None
    password: str | None = None; privateKey: str | None = None; userId: str | None = None
    connectTimeout: int | None = None; keepaliveInterval: int | None = None
    startupCommand: str | None = None; compression: bool | None = None; strictHostKeyCheck: bool | None = None
class TerminalOpen(APIModel): connectionId: str | None = None; cols: int | None = None; rows: int | None = None
class TerminalExec(APIModel): sessionId: str | None = None; command: str | None = None
class TerminalWrite(APIModel): sessionId: str | None = None; input: str | None = None
class TerminalResize(APIModel): sessionId: str | None = None; cols: int | None = None; rows: int | None = None


class KnowledgeDocumentRequest(APIModel):
    tenantId: str = "default"
    title: str
    content: str
    sourceType: str = "manual"
    sourceUri: str | None = None
    documentType: str = "operations"
    service: str | None = None
    environment: str | None = None
    version: str | None = None
    permissionScope: list[str] = Field(default_factory=list)


class KnowledgeSearchRequest(APIModel):
    tenantId: str = "default"
    query: str
    roles: list[str] = Field(default_factory=list)
    service: str | None = None
    environment: str | None = None
    topK: int | None = None


def envelope(data: Any = None, code: str = "0000", info: str = "成功") -> dict[str, Any]:
    # The public envelope always includes data, including a null value.
    return {"code": code, "info": info, "data": data}
