"""Durable application memory, independent from in-process graph execution."""
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence import ChatMessage, ChatMilestone, ChatSession


class ChatHistoryRepository:
    def __init__(self, db: AsyncSession): self.db = db

    async def session_exists(self, session_id: str) -> bool:
        return await self.db.get(ChatSession, session_id) is not None

    async def messages(self, session_id: str) -> list[dict]:
        query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at, ChatMessage.id)
        rows = (await self.db.execute(query)).scalars().all()
        return [{"role": x.role, "content": x.content or "", "toolName": x.tool_name,
                 "toolCallId": x.tool_call_id, "priority": x.priority or "MEDIUM"} for x in rows]

    async def add_message(self, session_id: str, role: str, content: str | None,
                          tool_name: str | None = None, tool_call_id: str | None = None,
                          priority: str = "MEDIUM") -> None:
        self.db.add(ChatMessage(session_id=session_id, role=role, content=content,
                                tool_name=tool_name, tool_call_id=tool_call_id,
                                priority=priority, token_count=len(content or "") // 2,
                                created_at=datetime.now()))
        session = await self.db.get(ChatSession, session_id)
        if session:
            session.message_count = (session.message_count or 0) + 1
            session.updated_at = datetime.now()

    async def add_milestone(self, session_id: str, kind: str, content: str) -> None:
        self.db.add(ChatMilestone(session_id=session_id, type=kind, content=content[:203], created_at=datetime.now()))

    async def detect_milestone(self, session_id: str, role: str, content: str | None) -> None:
        if not content: return
        kind=None
        if role=="user":
            if __import__('re').search("不对|不是这样|改一下|换个思路|换种方式|错了",content):kind="TASK_CHANGE"
            elif __import__('re').search("完成了|搞定|结束|好了",content):kind="TASK_COMPLETE"
            elif __import__('re').search("不要|停|别",content):kind="USER_CORRECTION"
        elif role=="tool" and __import__('re').search("error|failed|exception|permission denied|not found|refused",content,__import__('re').I):kind="ERROR"
        if kind: await self.add_milestone(session_id,kind,content[:200]+("..." if len(content)>200 else ""))

    async def milestones(self, session_id: str, limit: int = 10) -> list[dict]:
        query = (select(ChatMilestone).where(ChatMilestone.session_id == session_id)
                 .order_by(ChatMilestone.created_at.desc(), ChatMilestone.id.desc()).limit(limit))
        rows = list(reversed((await self.db.execute(query)).scalars().all()))
        return [{"type": x.type, "content": x.content or ""} for x in rows]
