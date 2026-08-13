from collections import defaultdict, deque
from dataclasses import dataclass, field
from app.ssh import ssh_manager


def tokens(message: dict) -> int: return len(str(message.get("content", ""))) // 2


class SlidingWindowReducer:
    def reduce(self, messages, budget):
        result=[]; used=0
        for message in reversed(messages):
            cost=tokens(message)
            if len(result)>=20 or used+cost>budget: break
            result.insert(0,message); used+=cost
        return result


class PriorityReducer:
    def reduce(self, messages, budget):
        if not messages: return []
        keep=list(messages[-min(2,len(messages)):]); used=sum(map(tokens,keep))
        for message in reversed(messages[:-len(keep)]):
            cost=tokens(message)
            if used+cost<=budget: keep.insert(0,message); used+=cost
        return keep


class HybridReducer:
    def reduce(self,messages,budget):
        priority=self._indices(PriorityReducer().reduce(messages,budget),messages)
        sliding=self._indices(SlidingWindowReducer().reduce(messages,budget),messages)
        keep=priority & sliding
        keep.update(range(max(0,len(messages)-2),len(messages)))
        return [m for i,m in enumerate(messages) if i in keep]
    @staticmethod
    def _indices(subset,all_messages):
        # Java List.indexOf behavior is intentionally retained for equal maps.
        return {all_messages.index(message) for message in subset}


class ToolResultProvider:
    def __init__(self): self.results=defaultdict(list); self.cache={}
    def push(self,sid,name,result): self.results[sid].append((name,result)); self.cache.pop(sid,None)
    def provide(self,sid):
        entries=self.results[sid]
        if not entries:return ""
        if sid not in self.cache:
            if len(entries)<=5:self.cache[sid]="\n".join(f"{n}: {self._cut(r,100)}" for n,r in entries)
            else:self.cache[sid]=f"最近执行了 {len(entries)} 个工具调用:\n"+"".join(f"- {n}: {self._cut(r,80)}\n" for n,r in entries[-5:])
        return self.cache[sid]
    @staticmethod
    def _cut(value,size): return (value or "") if len(value or "")<=size else value[:size]+"..."


tool_results=ToolResultProvider()


async def build_context(session_id, terminal_id, history, milestones):
    context={"taskDescription":next((m.get("content") for m in history if m.get("role")=="user"),None),
             "milestones":milestones,"toolResultSummary":tool_results.provide(session_id)}
    if terminal_id:
        for key,command in (("osInfo","uname -srm"),("currentUser","whoami"),("currentDirectory","pwd"),("uptime","uptime -p 2>/dev/null || uptime")):
            try: context[key]=(await ssh_manager.execute(terminal_id,command)).strip()
            except Exception: context[key]=""
    return context


def message_prefix(context,recent_commands=None):
    out=[]
    if any(context.get(k) for k in ("osInfo","currentUser","currentDirectory","serverInfo")):
        out.append("[系统环境]")
        for key,label in (("serverInfo","服务器"),("osInfo","系统"),("currentUser","用户"),("currentDirectory","目录")):
            if context.get(key):out.append(f"{label}: {context[key]}")
    if recent_commands:
        out.extend(["","[最近执行的命令]",*[f"- {x}" for x in recent_commands]])
    if context.get("milestones"):
        out.extend(["","[关键事件]",*[f"- [{x['type']}] {x['content']}" for x in context['milestones']]])
    if context.get("toolResultSummary"):out.extend(["","[工具执行摘要]",context["toolResultSummary"]])
    if context.get("taskDescription"):out.extend(["","[当前任务]",context["taskDescription"]])
    return "\n".join(out)
