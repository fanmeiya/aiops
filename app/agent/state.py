"""Explicit separation of application, Claude, terminal, connection and user IDs."""
from dataclasses import dataclass


@dataclass
class SessionMapping:
    user_id: str
    chat_session_id: str
    claude_session_id: str | None = None
    terminal_session_id: str | None = None
    connection_id: str | None = None


class SessionRegistry:
    def __init__(self): self._items: dict[str, SessionMapping] = {}
    def create(self,user_id,chat_id):
        self._items[chat_id]=SessionMapping(user_id,chat_id);return self._items[chat_id]
    def get(self,chat_id): return self._items.get(chat_id)
    def bind_terminal(self,chat_id,terminal_id,connection_id=None):
        item=self._items.get(chat_id)
        if item:item.terminal_session_id=terminal_id;item.connection_id=connection_id
    def set_claude(self,chat_id,claude_id):
        item=self._items.get(chat_id)
        if item:item.claude_session_id=claude_id
    def unbind(self,chat_id):
        item=self._items.get(chat_id)
        if item:item.terminal_session_id=None;item.connection_id=None


session_registry=SessionRegistry()
