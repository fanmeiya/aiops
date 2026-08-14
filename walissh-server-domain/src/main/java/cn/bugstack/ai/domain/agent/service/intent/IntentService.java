package cn.bugstack.ai.domain.agent.service.intent;

import cn.bugstack.ai.domain.agent.model.valobj.intent.ConversationContextVO;
import cn.bugstack.ai.domain.agent.model.valobj.intent.IntentResultVO;
import cn.bugstack.ai.domain.agent.service.IIntentService;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class IntentService implements IIntentService {

    @Resource
    private RuleIntentClassifier ruleClassifier;

    @Resource
    private LLMIntentClassifier llmClassifier;

    @Resource
    private ContextTracker contextTracker;

    // 简单的 LRU 缓存，最大 200 个条目
    private final Map<String, CacheEntry> cache = Collections.synchronizedMap(
        new LinkedHashMap<String, CacheEntry>(16, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, CacheEntry> eldest) {
                return size() > 200;
            }
        });

    private static class CacheEntry {
        IntentResultVO result;
        long expireTime;
        CacheEntry(IntentResultVO result, long expireTime) {
            this.result = result;
            this.expireTime = expireTime;
        }
    }

    @Override
    public IntentResultVO classify(String sessionId, String userId, String message) {
        String cacheKey = sessionId + ":" + hashMessage(message);
        
        CacheEntry cached = cache.get(cacheKey);
        if (cached != null && cached.expireTime > System.currentTimeMillis()) {
            return cached.result;
        }

        ConversationContextVO context = contextTracker.getContext(sessionId);

        // 第1层：规则分类（< 1ms）
        IntentResultVO ruleResult = ruleClassifier.classify(message, context);
        if (ruleResult.getConfidence() >= 0.8) {
            recordAndCache(sessionId, cacheKey, ruleResult);
            return ruleResult;
        }

        // 第2层：LLM 分类（100-500ms）
        IntentResultVO llmResult = llmClassifier.classify(message, context);
        IntentResultVO finalResult = llmResult.getConfidence() >= 0.5 ? llmResult : ruleResult;

        recordAndCache(sessionId, cacheKey, finalResult);
        return finalResult;
    }

    private void recordAndCache(String sessionId, String cacheKey, IntentResultVO result) {
        contextTracker.updateContext(sessionId, result);
        // 缓存 5 分钟
        cache.put(cacheKey, new CacheEntry(result, System.currentTimeMillis() + 5 * 60 * 1000));
    }

    private String hashMessage(String message) {
        return Integer.toHexString(message.hashCode());
    }
}
