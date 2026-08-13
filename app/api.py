import asyncio, json, os, posixpath, re, uuid
from datetime import datetime
from urllib.parse import quote
from fastapi import APIRouter, Body, Depends, File, Query, UploadFile
from fastapi.responses import Response as RawResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.persistence import ChatMessage, ChatSession, SshConnection, SshConnectionConfig, get_db
from app.schemas import *
from app.ssh import ssh_manager
from app.security import encrypt

router = APIRouter(prefix="/api/v1")
bindings: dict[str, str] = {}


def fail(exc, prefix=""):
    if isinstance(exc, (ValueError, KeyError)): return envelope(code="0002", info=str(exc).strip("'"))
    return envelope(code="0001", info=(prefix + str(exc)) if prefix else "未知失败")


def connection_dto(x):
    fmt = lambda d: d.strftime("%Y-%m-%d %H:%M:%S") if d else None
    return {"connectionId": x.connection_id, "connectionName": x.connection_name, "host": x.host,
            "port": x.port, "username": x.username, "authType": x.auth_type, "status": x.status,
            "encrypted": x.encrypted, "userId": x.user_id, "createdAt": fmt(x.created_at), "updatedAt": fmt(x.updated_at)}


async def records(db, cid):
    rec = (await db.execute(select(SshConnection).where(SshConnection.connection_id == cid, SshConnection.deleted == 0))).scalar_one_or_none()
    if not rec: raise ValueError("连接不存在")
    cfg = (await db.execute(select(SshConnectionConfig).where(SshConnectionConfig.connection_id == cid))).scalar_one_or_none()
    return rec, cfg or SshConnectionConfig(connection_id=cid)


@router.post("/ssh/create_connection")
async def create_connection(req: ConnectionRequest, db: AsyncSession = Depends(get_db)):
    try:
        if not req.connectionName or not req.host or not req.username: raise ValueError("连接名称、主机地址和用户名不能为空")
        now=datetime.now(); cid=str(uuid.uuid4())
        password,private_key,encrypted=req.password,req.privateKey,0
        if req.password or req.privateKey:
            password,private_key,encrypted=encrypt(req.password),encrypt(req.privateKey),1
        rec=SshConnection(connection_id=cid, connection_name=req.connectionName, host=req.host, port=req.port or 22,
          username=req.username, auth_type=req.authType or 1, password=password, private_key=private_key,
          encrypted=encrypted, status=0, user_id=req.userId or "default", created_at=now, updated_at=now)
        cfg=SshConnectionConfig(connection_id=cid, connect_timeout=req.connectTimeout or 10,
          keepalive_interval=req.keepaliveInterval or 60, startup_command=req.startupCommand,
          compression=req.compression or False, strict_host_key_check=True if req.strictHostKeyCheck is None else req.strictHostKeyCheck, updated_at=now)
        db.add_all([rec,cfg]); await db.commit(); return envelope(connection_dto(rec))
    except Exception as e: await db.rollback(); return fail(e)


@router.post("/ssh/update_connection")
async def update_connection(req: ConnectionRequest, db: AsyncSession = Depends(get_db)):
    try:
        if not req.connectionId: raise ValueError("连接ID不能为空")
        rec,cfg=await records(db,req.connectionId)
        password=encrypt(req.password) if req.password is not None else None
        private_key=encrypt(req.privateKey) if req.privateKey is not None else None
        for attr,val in [("connection_name",req.connectionName),("host",req.host),("port",req.port),("username",req.username),("auth_type",req.authType),("password",password),("private_key",private_key),("user_id",req.userId)]:
            if val is not None: setattr(rec,attr,val)
        if req.password is not None or req.privateKey is not None: rec.encrypted=1
        for attr,val in [("connect_timeout",req.connectTimeout),("keepalive_interval",req.keepaliveInterval),("startup_command",req.startupCommand),("compression",req.compression),("strict_host_key_check",req.strictHostKeyCheck)]:
            if val is not None: setattr(cfg,attr,val)
        rec.updated_at=datetime.now(); await db.commit(); return envelope(connection_dto(rec))
    except Exception as e: await db.rollback(); return fail(e)


@router.post("/ssh/delete_connection")
async def delete_connection(connectionId: str, db: AsyncSession=Depends(get_db)):
    try: rec,_=await records(db,connectionId); rec.deleted=1; await ssh_manager.disconnect(connectionId); await db.commit(); return envelope()
    except Exception as e: return fail(e)


@router.get("/ssh/get_connection")
async def get_connection(connectionId: str, db: AsyncSession=Depends(get_db)):
    try: rec,_=await records(db,connectionId); return envelope(connection_dto(rec))
    except Exception as e: return fail(e)


@router.get("/ssh/connection_list")
async def connection_list(userId: str="default", db: AsyncSession=Depends(get_db)):
    rows=(await db.execute(select(SshConnection).where(SshConnection.user_id==userId,SshConnection.deleted==0))).scalars().all()
    for x in rows: x.status=1 if x.connection_id in ssh_manager.connections and not ssh_manager.connections[x.connection_id].is_closed() else 0
    return envelope([connection_dto(x) for x in rows])


@router.post("/ssh/connect")
async def connect(connectionId: str, db: AsyncSession=Depends(get_db)):
    try: rec,cfg=await records(db,connectionId); await ssh_manager.connect(rec,cfg); rec.status=1; await db.commit(); return envelope(info="连接成功")
    except Exception as e: return envelope(code="0001",info="连接失败: "+str(e))


@router.post("/ssh/disconnect")
async def disconnect(connectionId: str, db: AsyncSession=Depends(get_db)):
    try: await ssh_manager.disconnect(connectionId); rec,_=await records(db,connectionId); rec.status=0; await db.commit(); return envelope(info="已断开连接")
    except Exception as e: return envelope(code="0001",info="断开连接失败: "+str(e))


@router.post("/ssh/terminal/open")
async def terminal_open(req: TerminalOpen, db: AsyncSession=Depends(get_db)):
    try:
        _,cfg=await records(db,req.connectionId); term=await ssh_manager.open(req.connectionId,req.cols or 120,req.rows or 24,cfg.startup_command)
        await asyncio.sleep(.05); initial=ssh_manager.read(term.session_id)
        return envelope({"sessionId":term.session_id,"connectionId":req.connectionId,"initialOutput":initial})
    except Exception as e: return fail(e,"打开终端失败: ")

@router.post("/ssh/terminal/exec")
async def terminal_exec(req: TerminalExec):
    try: return envelope({"output":await ssh_manager.execute(req.sessionId,req.command or "")})
    except Exception as e: return fail(e,"执行命令失败: ")
@router.post("/ssh/terminal/write")
async def terminal_write(req: TerminalWrite):
    try: await ssh_manager.write(req.sessionId,req.input or ""); return envelope()
    except Exception as e: return fail(e,"写入终端失败: ")
@router.get("/ssh/terminal/read")
async def terminal_read(sessionId: str):
    try: return envelope({"output":ssh_manager.read(sessionId)})
    except Exception as e: return fail(e,"读取终端失败: ")
@router.post("/ssh/terminal/resize")
async def terminal_resize(req: TerminalResize):
    try: await ssh_manager.resize(req.sessionId,req.cols,req.rows); return envelope()
    except Exception as e: return envelope(code="0001",info="调整终端大小失败: "+str(e))
@router.post("/ssh/terminal/close")
async def terminal_close(sessionId: str):
    try: await ssh_manager.close(sessionId); return envelope()
    except Exception as e: return envelope(code="0001",info="关闭终端会话失败: "+str(e))


async def sftp(cid): return await ssh_manager.sftp_connection(cid).start_sftp_client()
def norm(path):
    if not path: raise ValueError("路径不能为空")
    return posixpath.normpath(path if path.startswith("/") else "/"+path)
def binary(data): return b"\0" in data[:8192] or (bool(data) and sum(b<9 or 13<b<32 for b in data[:8192])/len(data[:8192])>.3)

@router.get("/ssh/file/tree")
async def file_tree(connectionId: str,path: str|None=None):
    try:
        client=await sftp(connectionId); home=await client.realpath("."); cur=norm(path or home); names=await client.listdir(cur); items=[]
        for name in names[:500]:
            p=posixpath.join(cur,name); a=await client.stat(p); directory=a.type==2
            items.append({"name":name,"path":p,"directory":directory,"size":None if directory else a.size,"modifiedAt":int(a.mtime*1000) if a.mtime else None})
        items.sort(key=lambda x:(not x["directory"],x["name"].lower()))
        return envelope({"rootPath":"/","homePath":home,"currentPath":cur,"parentPath":None if cur=="/" else posixpath.dirname(cur),"items":items})
    except Exception as e:return fail(e,"查询目录失败: ")

async def content_impl(cid,path,offset=0,limit=256*1024):
    client=await sftp(cid); p=norm(path); attrs=await client.stat(p); limit=min(limit or 256*1024,256*1024); offset=max(offset or 0,0)
    async with client.open(p,"rb") as f: await f.seek(offset); data=await f.read(min(limit,max(attrs.size-offset,0)))
    isbin=binary(data); used=len(data)
    return {"path":p,"name":posixpath.basename(p),"charset":"UTF-8","size":attrs.size,"binary":isbin,
            "truncated":used<max(attrs.size-offset,0),"offset":offset,"remaining":max(0,attrs.size-offset-used),"content":"" if isbin else data.decode("utf-8",errors="replace")}
@router.get("/ssh/file/content")
async def file_content(connectionId:str,path:str):
    try:return envelope(await content_impl(connectionId,path))
    except Exception as e:return fail(e,"读取文件失败: ")
@router.get("/ssh/file/content-chunk")
async def file_chunk(connectionId:str,path:str,offset:int|None=None,limit:int|None=None):
    try:return envelope(await content_impl(connectionId,path,offset,limit))
    except Exception as e:return fail(e,"读取文件失败: ")

async def file_mutate(action,cid,path,other=None):
    client=await sftp(cid); p=norm(path)
    if action=="touch":
        async with client.open(p,"wb"): pass
    elif action=="mkdir": await client.mkdir(p)
    elif action=="rename": await client.rename(p,norm(other))
    elif action=="delete":
        a=await client.stat(p)
        if a.type==2:
            for n in await client.listdir(p): await file_mutate("delete",cid,posixpath.join(p,n))
            await client.rmdir(p)
        else: await client.remove(p)

@router.post("/ssh/file/create-file")
async def create_file(connectionId:str,path:str,sudo:bool=False):
    try: await file_mutate("touch",connectionId,path); return envelope(info="创建文件成功")
    except Exception as e:return fail(e,"创建文件失败: ")
@router.post("/ssh/file/create-directory")
async def create_directory(connectionId:str,path:str,sudo:bool=False):
    try: await file_mutate("mkdir",connectionId,path); return envelope(info="创建目录成功")
    except Exception as e:return fail(e,"创建目录失败: ")
@router.post("/ssh/file/rename")
async def rename_file(connectionId:str,oldPath:str,newPath:str,sudo:bool=False):
    try: await file_mutate("rename",connectionId,oldPath,newPath); return envelope(info="重命名成功")
    except Exception as e:return fail(e,"重命名失败: ")
@router.post("/ssh/file/delete")
async def delete_file(connectionId:str,path:str,sudo:bool=False):
    try: await file_mutate("delete",connectionId,path); return envelope(info="删除成功")
    except Exception as e:return fail(e,"删除失败: ")
@router.post("/ssh/file/save-content")
async def save_file(connectionId:str,path:str,sudo:bool=False,body:dict=Body(...)):
    try:
        client=await sftp(connectionId)
        async with client.open(norm(path),"wb") as f: await f.write(body.get("content","").encode())
        return envelope(info="保存文件成功")
    except Exception as e:return fail(e,"保存文件失败: ")
@router.post("/ssh/file/upload")
async def upload(connectionId:str,path:str,file:UploadFile=File(...)):
    try:
        client=await sftp(connectionId)
        async with client.open(norm(path),"wb") as f:
            while chunk:=await file.read(65536): await f.write(chunk)
        return envelope(info="上传文件成功")
    except Exception as e:return fail(e,"上传文件失败: ")
@router.get("/ssh/file/download")
async def download(connectionId:str,path:str):
    try:
        client=await sftp(connectionId); f=await client.open(norm(path),"rb")
        async def chunks():
            async with f:
                while data:=await f.read(65536): yield data
        return StreamingResponse(chunks(),media_type="application/octet-stream",headers={"Content-Disposition":"attachment; filename="+quote(posixpath.basename(path))})
    except Exception:return RawResponse(status_code=500)


@router.post("/ssh/agent/bind_terminal")
async def bind(req:Binding):
    if not req.chatSessionId:return envelope(code="0002",info="chatSessionId 不能为空")
    if not req.terminalSessionId:return envelope(code="0002",info="terminalSessionId 不能为空")
    bindings[req.chatSessionId]=req.terminalSessionId; return envelope({"chatSessionId":req.chatSessionId,"terminalSessionId":req.terminalSessionId,"bound":True})
@router.post("/ssh/agent/unbind_terminal")
async def unbind(chatSessionId:str):bindings.pop(chatSessionId,None);return envelope()
@router.get("/ssh/agent/query_binding")
async def query_binding(chatSessionId:str):
    tid=bindings.get(chatSessionId); return envelope({"chatSessionId":chatSessionId,"terminalSessionId":tid,"bound":bool(tid)},info="成功" if tid else "未绑定终端")
