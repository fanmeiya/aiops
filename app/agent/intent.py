import json, re, time
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from app.agent.model import deepseek_client
from app.config import settings

RULES = {
"DIAGNOSE":(["挂了","宕机","down","502","503","504","oom","满","过高","异常","报错","告警","超时","timeout","crash","panic","fatal"],[r"为什么.*(?:挂|报错|失败|不通)",r"排查.*问题",r"分析.*原因"]),
"CONFIGURE":(["配置","config","修改配置","参数","调整","设置","调优"],[r"修改.*(?:conf|cfg|yml|properties|xml|json)",r"设置.*参数"]),
"DEPLOY":(["部署","deploy","发布","回滚","rollback","上线","更新版本","重启服务"],[r"(?:发布|部署).*版本",r"回滚.*版本"]),
"MONITOR":(["查看","监控","日志","log","cpu","内存","磁盘","网络","流量","负载","load","进程","端口","连接数"],[r"(?:看|查|check).*(?:状态|情况|使用率)",r"tail.*log"]),
"SECURITY":(["防火墙","firewall","iptables","权限","permission","ssh","密钥","证书","ssl","tls","安全","漏洞","cve"],[r"(?:开放|关闭).*端口",r"配置.*(?:ssl|证书|密钥)"]),
"BACKUP":(["备份","backup","恢复","restore","导出","import","迁移"],[r"备份.*(?:数据库|文件|配置)",r"恢复.*数据"]),
"EXPLAIN":(["什么意思","怎么理解","解释","说明","explain","what is","how to"],[r"这个命令.*(?:意思|作用|用途)"]),
"SEARCH":(["找","搜索","grep","find","locate","查找","哪个进程","哪个文件"],[r"(?:找|搜索).*(?:文件|进程|端口)"])}

class IntentService:
    def __init__(self):self.history=defaultdict(lambda:deque(maxlen=10));self.cache=OrderedDict()
    def rule_classify(self,sid,message):
        key=(sid,message); now=time.time()
        if key in self.cache and self.cache[key][0]>now:return self.cache[key][1]
        lower=message.lower(); best={"intent":"UNKNOWN","confidence":0.0,"entities":{}}
        for intent,(words,patterns) in RULES.items():
            score=min(.6,sum(word in lower for word in words)*.2)
            if any(re.search(pattern,message,re.I) for pattern in patterns):score+=.2
            if any(x["intent"]==intent for x in self.history[sid]):score+=.1
            if min(score,1)>best["confidence"]:
                entities={};
                for service in ("nginx","redis","mysql","postgres","docker","kafka","rabbitmq","elasticsearch"):
                    if service in lower:entities["service"]=service
                best={"intent":intent,"confidence":min(score,1),"entities":entities}
        self.history[sid].append(best);self.cache[key]=(now+300,best)
        while len(self.cache)>200:self.cache.popitem(last=False)
        return best

    async def classify(self,sid,message):
        rule=self.rule_classify(sid,message)
        if rule["confidence"]>=.8:return rule
        try:
            prompt=("只返回JSON，不要markdown。字段为intent、confidence、entities。intent只能是 "
                    +", ".join([*RULES,"UNKNOWN"])+"。用户消息："+message)
            response = await deepseek_client().chat.completions.create(
                model=settings.deepseek_model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
            )
            text = response.choices[0].message.content or "{}"
            parsed=json.loads(text[text.find("{"):text.rfind("}")+1])
            llm={"intent":str(parsed.get("intent","UNKNOWN")).upper(),"confidence":float(parsed.get("confidence",0)),"entities":parsed.get("entities") or {}}
            result=llm if llm["confidence"]>=.5 else rule
            self.history[sid].append(result);self.cache[(sid,message)]=(time.time()+300,result)
            return result
        except Exception:
            return rule

intent_service=IntentService()
