import json
from app.schemas import envelope


def encode(event):
    return json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'


def test_stream_is_ndjson_not_sse():
    wire=encode({'event':'text','content':'中','fullText':'中'})
    assert wire.endswith('\n') and not wire.startswith('data:')
    assert json.loads(wire)['event']=='text'


def test_response_envelope_keeps_null_data():
    assert envelope()=={'code':'0000','info':'成功','data':None}
