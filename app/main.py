import json, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import router, bindings
from app.agent.runtime import runtime
from app.persistence import ChatMessage, ChatSession, get_db, init_database
from app.schemas import ChatRequest, CreateSession, envelope
from app.memory import ChatHistoryRepository
from app.agent.context import HybridReducer, build_context, conversation_history, message_prefix
from app.agent.intent import intent_service
from app.agent.state import session_registry
from app.config import settings

@asynccontextmanager
async def lifespan(app):
    await init_database(); yield

app=FastAPI(title='WaLiSSH Server', lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_methods=['*'],allow_headers=['*'],allow_credentials=False)
app.include_router(router)

@app.get('/api/v1/query_ai_agent_config_list')
async def agent_list():
    return envelope([{'agentId':'100000','agentName':'SSH AI Agent','agentDesc':'SSH 智能运维助手，可执行远程命令并智能分析结果'}])

async def make_session(agent,user,db):
    if agent!='100000': return None
    sid=str(uuid.uuid4()); now=__import__('datetime').datetime.now()
    db.add(ChatSession(id=sid,agent_id=agent,user_id=user,title=None,message_count=0,created_at=now,updated_at=now))
    session_registry.create(user,sid); await db.commit(); return sid

async def prepare(req,sid,terminal_id,db):
    repo=ChatHistoryRepository(db); history=await repo.messages(sid)
    intent=await intent_service.classify(sid,req.message or '')
    milestones=await repo.milestones(sid)
    trimmed=HybridReducer().reduce(history,8000)
    context=await build_context(sid,terminal_id,trimmed,milestones)
    prefix=message_prefix(context)
    mapping=session_registry.get(sid)
    restored_history="" if mapping and mapping.claude_session_id else conversation_history(trimmed)
    parts=[part for part in (restored_history,prefix,req.message or '') if part]
    enriched='\n---\n'.join(parts)
    return repo,enriched,intent

@app.post('/api/v1/create_session')
async def create(req:CreateSession,db:AsyncSession=Depends(get_db)):
    sid=await make_session(req.agentId,req.userId,db)
    return envelope({'sessionId':sid}) if sid else envelope(code='E0001',info='智能体ID不存在')
@app.get('/api/v1/create_session')
async def create_get(agentId:str,userId:str,db:AsyncSession=Depends(get_db)):
    return await create(CreateSession(agentId=agentId,userId=userId),db)

@app.post('/api/v1/chat')
async def chat(req:ChatRequest,db:AsyncSession=Depends(get_db)):
    sid=req.sessionId or await make_session(req.agentId,req.userId,db)
    if not sid:return envelope(code='E0001',info='智能体ID不存在')
    req.sessionId=sid
    terminal=req.terminalSessionId or bindings.get(sid); repo,enriched,intent=await prepare(req,sid,terminal,db)
    await repo.add_message(sid,'user',req.message); await repo.detect_milestone(sid,'user',req.message); text=''
    async for event in runtime.stream(req,terminal,enriched):
        if event['event']=='done': text=event['fullText'] or ''
        elif event['event']=='tool_result':
            await repo.add_message(sid,'tool',event['content'],'executeCommand',event['toolCallId']); await repo.detect_milestone(sid,'tool',event['content'])
    await repo.add_message(sid,'assistant',text)
    await db.commit(); return envelope({'content':text})

@app.post('/api/v1/chat_stream')
async def chat_stream(req:ChatRequest,db:AsyncSession=Depends(get_db)):
    sid=req.sessionId or await make_session(req.agentId,req.userId,db); req.sessionId=sid
    if not sid:
        async def invalid(): yield json.dumps({'event':'error','content':'智能体ID不存在'},ensure_ascii=False)+'\n'
        return StreamingResponse(invalid(),media_type='application/json')
    terminal=req.terminalSessionId or bindings.get(sid); repo,enriched,intent=await prepare(req,sid,terminal,db)
    await repo.add_message(sid,'user',req.message); await repo.detect_milestone(sid,'user',req.message); await db.commit()
    async def generate():
        final=''
        try:
            async for event in runtime.stream(req,terminal,enriched):
                if event['event']=='tool_result':
                    await repo.add_message(sid,'tool',event['content'],'executeCommand',event['toolCallId']); await repo.detect_milestone(sid,'tool',event['content'])
                if event['event']=='done': final=event.get('fullText') or ''
                yield json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'
        finally:
            if final: await repo.add_message(sid,'assistant',final)
            await db.commit()
    # Java ResponseBodyEmitter writes JSON plus newline, not SSE data frames.
    return StreamingResponse(generate(),media_type='application/json')
