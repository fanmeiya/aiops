package cn.bugstack.ai.domain.agent.service.context.provider;

import cn.bugstack.ai.domain.ssh.service.ISshTerminalService;
import org.springframework.stereotype.Component;

import jakarta.annotation.Resource;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Component
public class TerminalStateProvider implements ContextProvider {
    @Resource
    private ISshTerminalService sshTerminalService;

    @Override public String getName() { return "terminal-state"; }
    @Override public int getOrder() { return 10; }
    @Override public boolean enabled() { return true; }

    @Override
    public Map<String, Object> provide(String sessionId, String userId, String terminalSessionId, List<Map<String, Object>> messageHistory) {
        Map<String, Object> result = new HashMap<>();
        
        if (terminalSessionId == null || terminalSessionId.isEmpty()) {
            return result;
        }

        String osInfo = safeExec(terminalSessionId, "uname -srm");
        String user   = safeExec(terminalSessionId, "whoami");
        String pwd    = safeExec(terminalSessionId, "pwd");
        String uptime = safeExec(terminalSessionId, "uptime -p 2>/dev/null || uptime");

        result.put("osInfo", osInfo);
        result.put("currentUser", user);
        result.put("currentDirectory", pwd);
        result.put("uptime", uptime);
        return result;
    }

    private String safeExec(String terminalSessionId, String cmd) {
        try {
            String res = sshTerminalService.executeCommand(terminalSessionId, cmd);
            return res != null ? res.trim() : "";
        } catch (Exception e) { 
            return ""; 
        }
    }
}
