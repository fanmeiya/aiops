from app.agent.intent import IntentService
from app.agent.permissions import check_permission


def test_rule_intent_context_boost_and_entities():
    service=IntentService()
    result=service.rule_classify('s','查看 docker CPU 和内存')
    assert result['intent']=='MONITOR'
    assert result['entities']=={'service':'docker'}
    assert result['confidence']==0.6
    second=service.rule_classify('s','再查看一下状态')
    assert second['intent']=='MONITOR'
    assert second['confidence'] >= 0.5


def test_sliding_priority_and_hybrid_reducers():
    # Import is deferred so this pure-domain test can also be run in the full environment.
    from app.agent.context import SlidingWindowReducer,PriorityReducer,HybridReducer
    messages=[{'role':'user','content':str(i)*10} for i in range(25)]
    assert len(SlidingWindowReducer().reduce(messages,1000))==20
    assert PriorityReducer().reduce(messages,10)==messages[-2:]
    assert HybridReducer().reduce(messages,10)==messages[-2:]


def test_destructive_command_requires_explicit_confirmation():
    import pytest
    with pytest.raises(PermissionError): check_permission('rm -rf /', '删除一些缓存')
    check_permission('rm -rf /', '我确认执行删除根目录')
