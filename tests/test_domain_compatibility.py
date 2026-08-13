from app.agent.intent import IntentService


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
