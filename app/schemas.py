from typing import Any
from pydantic import BaseModel, ConfigDict


class JavaModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CreateSession(JavaModel): agentId: str | None = None; userId: str | None = None
class ChatRequest(JavaModel):
    agentId: str | None = None; userId: str | None = None; sessionId: str | None = None
    message: str | None = None; terminalSessionId: str | None = None
class Binding(JavaModel): chatSessionId: str | None = None; terminalSessionId: str | None = None
class ConnectionRequest(JavaModel):
    connectionId: str | None = None; connectionName: str | None = None; host: str | None = None
    port: int | None = None; username: str | None = None; authType: int | None = None
    password: str | None = None; privateKey: str | None = None; userId: str | None = None
    connectTimeout: int | None = None; keepaliveInterval: int | None = None
    startupCommand: str | None = None; compression: bool | None = None; strictHostKeyCheck: bool | None = None
class TerminalOpen(JavaModel): connectionId: str | None = None; cols: int | None = None; rows: int | None = None
class TerminalExec(JavaModel): sessionId: str | None = None; command: str | None = None
class TerminalWrite(JavaModel): sessionId: str | None = None; input: str | None = None
class TerminalResize(JavaModel): sessionId: str | None = None; cols: int | None = None; rows: int | None = None


def envelope(data: Any = None, code: str = "0000", info: str = "成功") -> dict[str, Any]:
    # Jackson omits nothing in Response itself; absent generic data serializes as null.
    return {"code": code, "info": info, "data": data}
