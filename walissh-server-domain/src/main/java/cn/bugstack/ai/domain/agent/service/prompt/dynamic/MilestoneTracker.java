package cn.bugstack.ai.domain.agent.service.prompt.dynamic;

import cn.bugstack.ai.domain.agent.adapter.repository.IChatHistoryRepository;
import cn.bugstack.ai.domain.agent.model.valobj.prompt.MilestoneVO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import jakarta.annotation.Resource;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;

@Slf4j
@Component
public class MilestoneTracker {

    @Resource
    private IChatHistoryRepository chatHistoryRepository;

    private static final int MAX_MILESTONES = 50;
    private final Map<String, LinkedList<MilestoneVO>> milestones = new ConcurrentHashMap<>();

    public void detectAndRecord(String sessionId, String role, String content) {
        if (sessionId == null || content == null || content.isEmpty()) return;

        MilestoneVO.Type type = null;

        if ("user".equals(role)) {
            if (matches(content, "不对|不是这样|改一下|换个思路|换种方式|错了")) {
                type = MilestoneVO.Type.TASK_CHANGE;
            } else if (matches(content, "完成了|搞定|结束|好了")) {
                type = MilestoneVO.Type.TASK_COMPLETE;
            } else if (matches(content, "不要|停|别")) {
                type = MilestoneVO.Type.USER_CORRECTION;
            }
        }

        if ("tool".equals(role)) {
            if (matches(content, "(?i)error|failed|exception|permission denied|not found|refused")) {
                type = MilestoneVO.Type.ERROR;
            }
        }

        if (type != null) {
            push(sessionId, MilestoneVO.builder()
                    .type(type)
                    .content(truncate(content, 200))
                    .timestamp(System.currentTimeMillis())
                    .build());
            log.info("里程碑记录: sessionId={}, type={}, content={}", sessionId, type, truncate(content, 100));
        }
    }

    private void push(String sessionId, MilestoneVO milestoneVO) {
        LinkedList<MilestoneVO> list = milestones.computeIfAbsent(sessionId, k -> new LinkedList<>());
        synchronized (list) {
            list.addLast(milestoneVO);
            while (list.size() > MAX_MILESTONES) {
                list.removeFirst();
            }
        }

        // [Phase 5] 异步保存里程碑到数据库
        try {
            chatHistoryRepository.saveMilestone(sessionId, milestoneVO);
        } catch (Exception e) {
            log.error("保存里程碑失败", e);
        }
    }

    public List<MilestoneVO> getRecent(String sessionId, int limit) {
        // 优先从数据库读取，以保证会话重启后仍然有效
        try {
            List<MilestoneVO> recentMilestones = chatHistoryRepository.getRecentMilestones(sessionId, limit);
            if (recentMilestones != null && !recentMilestones.isEmpty()) {
                // 因为返回的是时间倒序（最新的在前），LLM需要最新的在后，可以反转一下
                List<MilestoneVO> reversed = new ArrayList<>(recentMilestones);
                Collections.reverse(reversed);
                return reversed;
            }
        } catch (Exception e) {
            log.error("获取近期里程碑失败", e);
        }

        // 降级回内存
        LinkedList<MilestoneVO> list = milestones.getOrDefault(sessionId, new LinkedList<>());
        synchronized (list) {
            int from = Math.max(0, list.size() - limit);
            return new ArrayList<>(list.subList(from, list.size()));
        }
    }

    public void clear(String sessionId) {
        milestones.remove(sessionId);
    }

    private boolean matches(String content, String regex) {
        return Pattern.compile(".*(" + regex + ").*").matcher(content).matches();
    }

    private String truncate(String s, int max) {
        if (s == null) return "";
        return s.length() > max ? s.substring(0, max) + "..." : s;
    }
}
