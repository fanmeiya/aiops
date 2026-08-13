import json, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import router, bindings
from app.agent.runtime import runtime
from app.persistence import ChatMessage, ChatSession, get_db, init_database
from app.schemas import ChatRequest, CreateSession, envelope

@asynccontextmanager
async def lifespan(app):
    await init_database(); yield

app=FastAPI(title='WaLiSSH Server', lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'],allow_credentials=False)
app.include_router(router)

@app.get('/api/v1/query_ai_agent_config_list')
async def agent_list():
    return envelope([{'agentId':'100000','agentName':'SSH AI Agent','agentDesc':'SSH 智能运维助手，可执行远程命令并智能分析结果'}])

async def make_session(agent,user,db):
    if agent!='100000': return None
    sid=str(uuid.uuid4()); db.add(ChatSession(id=sid,agent_id=agent,user_id=user,title=None,message_count=0)); await db.commit(); return sid

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
    text=''
    async for event in runtime.stream(req,req.terminalSessionId or bindings.get(sid)):
        if event['event']=='done': text=event['fullText'] or ''
    db.add_all([ChatMessage(session_id=sid,role='user',content=req.message),ChatMessage(session_id=sid,role='assistant',content=text)])
    await db.commit(); return envelope({'content':text})

@app.post('/api/v1/chat_stream')
async def chat_stream(req:ChatRequest,db:AsyncSession=Depends(get_db)):
    sid=req.sessionId or await make_session(req.agentId,req.userId,db); req.sessionId=sid
    async def generate():
        async for event in runtime.stream(req,req.terminalSessionId or bindings.get(sid)):
            yield json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'
    # Java ResponseBodyEmitter writes JSON plus newline, not SSE data frames.
    return StreamingResponse(generate(),media_type='application/json')
