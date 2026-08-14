import os
os.environ['WALISSH_DATABASE_URL']='sqlite+aiosqlite:///:memory:'
from fastapi.testclient import TestClient
from app.main import app

def test_agent_and_session_envelopes():
    with TestClient(app) as c:
        result=c.get('/api/v1/query_ai_agent_config_list').json()
        assert result['code']=='0000' and result['data'][0]['agentId']=='100000'
        result=c.post('/api/v1/create_session',json={'agentId':'bad','userId':'u'}).json()
        assert result == {'code':'E0001','info':'智能体ID不存在','data':None}

def test_binding_null_and_query_behavior():
    with TestClient(app) as c:
        assert c.post('/api/v1/ssh/agent/bind_terminal',json={}).json()['info']=='chatSessionId 不能为空'
        assert c.get('/api/v1/ssh/agent/query_binding',params={'chatSessionId':'c'}).json()=={
            'code':'0000','info':'未绑定终端','data':{'chatSessionId':'c','terminalSessionId':None,'bound':False}}

def test_terminal_defaults_are_in_openapi():
    with TestClient(app) as c:
        paths=c.get('/openapi.json').json()['paths']
        assert '/api/v1/ssh/terminal/open' in paths
        assert '/api/v1/ssh/file/content-chunk' in paths
