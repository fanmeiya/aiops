from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Index, UniqueConstraint, func
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from app.config import settings


class Base(AsyncAttrs, DeclarativeBase): pass


class SshConnection(Base):
    __tablename__ = "ssh_connection"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    connection_id: Mapped[str] = mapped_column(String(64), unique=True)
    connection_name: Mapped[str] = mapped_column(String(128))
    host: Mapped[str] = mapped_column(String(255)); port: Mapped[int] = mapped_column(Integer, default=22)
    username: Mapped[str] = mapped_column(String(128)); auth_type: Mapped[int] = mapped_column(Integer, default=1)
    password: Mapped[str | None] = mapped_column(String(512)); private_key: Mapped[str | None] = mapped_column(Text)
    encrypted: Mapped[int] = mapped_column(Integer, default=0); status: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[str] = mapped_column(String(64), default="default")
    created_at: Mapped[datetime | None] = mapped_column(DateTime); updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class SshConnectionConfig(Base):
    __tablename__ = "ssh_connection_config"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    connection_id: Mapped[str] = mapped_column(String(64), unique=True)
    connect_timeout: Mapped[int | None] = mapped_column(Integer, default=10)
    keepalive_interval: Mapped[int | None] = mapped_column(Integer, default=60)
    startup_command: Mapped[str | None] = mapped_column(String(512)); compression: Mapped[bool | None] = mapped_column(Boolean, default=False)
    strict_host_key_check: Mapped[bool | None] = mapped_column(Boolean, default=True)
    known_hosts: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatSession(Base):
    __tablename__ = "chat_session"
    id: Mapped[str] = mapped_column(String(64), primary_key=True); agent_id: Mapped[str] = mapped_column(String(64)); user_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(200)); created_at: Mapped[datetime | None] = mapped_column(DateTime); updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    message_count: Mapped[int] = mapped_column(Integer, default=0)


class ChatMessage(Base):
    __tablename__ = "chat_message"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True); session_id: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20)); content: Mapped[str | None] = mapped_column(Text); tool_name: Mapped[str | None] = mapped_column(String(100))
    tool_call_id: Mapped[str | None] = mapped_column(String(100)); priority: Mapped[str | None] = mapped_column(String(20), default="MEDIUM")
    token_count: Mapped[int | None] = mapped_column(Integer, default=0); created_at: Mapped[datetime | None] = mapped_column(DateTime)


class ChatMilestone(Base):
    __tablename__ = "chat_milestone"
    __table_args__ = (Index("idx_session_time", "session_id", "created_at"),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class SshSessionLog(Base):
    __tablename__ = "ssh_session_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    connection_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    status: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remote_addr: Mapped[str | None] = mapped_column(String(64))
    start_time: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    error_msg: Mapped[str | None] = mapped_column(String(512))


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_document"
    __table_args__ = (
        Index("idx_knowledge_document_tenant", "tenant_id", "status"),
        UniqueConstraint("tenant_id", "checksum", name="uk_knowledge_checksum"),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="manual")
    source_uri: Mapped[str | None] = mapped_column(String(512))
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="operations")
    service: Mapped[str | None] = mapped_column(String(128))
    environment: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[str | None] = mapped_column(String(64))
    permission_scope: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunk"
    __table_args__ = (Index("idx_knowledge_chunk_document", "document_id", "chunk_index"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_document.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str | None] = mapped_column(String(255))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


class KnowledgeQueryLog(Base):
    __tablename__ = "knowledge_query_log"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(64))
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    retrieved_chunk_ids: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.now())


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db():
    async with SessionLocal() as session: yield session


async def init_database():
    if settings.database_url.startswith("sqlite"):
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
