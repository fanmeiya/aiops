"""Deterministic command policy applied before every remote tool execution."""
import re

DESTRUCTIVE = (
    re.compile(r'(^|[;&|]\s*)rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)'),
    re.compile(r'\bmkfs(?:\.|\s)'),
    re.compile(r'\bdd\s+[^\n]*\bof=/dev/'),
    re.compile(r'\b(?:DROP\s+(?:DATABASE|TABLE)|TRUNCATE\s+TABLE)\b', re.I),
    re.compile(r'\b(?:shutdown|reboot|poweroff)\b'),
)
CONFIRMATION = re.compile(
    r"(?:确认|同意|允许|继续).{0,12}(?:执行|删除|格式化|重启|关机)"
    r"|(?:执行|删除|格式化|重启|关机).{0,12}(?:确认|同意|允许)"
)


def check_permission(command: str, user_message: str = "") -> None:
    if any(pattern.search(command) for pattern in DESTRUCTIVE):
        if not CONFIRMATION.search(user_message or ""):
            raise PermissionError("高风险命令需要用户明确确认，已阻止执行")
