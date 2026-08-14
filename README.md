# WaLiSSH Python 智能运维服务

WaLiSSH 是一个完全使用 Python 构建的远程智能运维后端。服务通过 FastAPI 暴露兼容接口，使用 LangGraph 编排 Agent 工作流，通过 DeepSeek API 完成模型推理，并使用 AsyncSSH 管理 SSH、交互式 PTY 和 SFTP。

## 技术栈

- Python 3.11+
- FastAPI 与 Uvicorn
- Pydantic v2 与 pydantic-settings
- LangGraph
- DeepSeek OpenAI-compatible API
- AsyncSSH
- SQLAlchemy 2.x Async 与 MySQL
- AES-256-GCM 凭据加密
- pytest

项目不直接依赖 LangChain。模型请求由 OpenAI-compatible 异步客户端发送，Agent 的模型节点、工具节点、循环条件和终止条件由 LangGraph 管理。

## 功能

- Agent 配置查询、会话创建、同步聊天和 NDJSON 流式聊天
- DeepSeek 工具调用与受限 ReAct 循环
- SSH 连接配置的创建、查询、更新、删除、连接和断开
- 持久交互式 PTY 的打开、读写、命令执行、缩放和关闭
- SFTP 目录浏览、分块读取、创建、重命名、删除、保存、上传和下载
- Chat session 与 Terminal session 显式绑定
- 聊天消息、工具结果和里程碑持久化
- 上下文裁剪、意图识别和命令风险检查
- 应用关闭时统一释放 PTY、SFTP 和 SSH 连接

## 项目结构

```text
app/
├── main.py                 # FastAPI 应用、会话和聊天接口
├── api.py                  # SSH、PTY、SFTP 和终端绑定接口
├── config.py               # 环境变量配置
├── schemas.py              # Pydantic 请求与响应模型
├── persistence.py          # SQLAlchemy 数据模型和异步会话
├── memory.py               # 聊天历史与里程碑
├── security.py             # 凭据加密
├── ssh.py                  # AsyncSSH 连接、PTY 和 SFTP 管理
└── agent/
    ├── model.py            # DeepSeek 客户端
    ├── runtime.py          # LangGraph Agent 工作流
    ├── context.py          # 上下文提供与裁剪
    ├── intent.py           # 规则与 DeepSeek 意图识别
    ├── permissions.py      # 确定性命令安全策略
    ├── state.py            # 会话与终端映射
    └── ssh-agent.yml       # 智能运维提示词
```

## 配置

复制环境变量模板：

```bash
cp .env.example .env
```

至少配置：

```dotenv
WALISSH_DATABASE_URL=mysql+aiomysql://user:password@127.0.0.1:3306/walissh
WALISSH_DEEPSEEK_API_KEY=your-api-key
WALISSH_DEEPSEEK_BASE_URL=https://api.deepseek.com
WALISSH_DEEPSEEK_MODEL=deepseek-chat
WALISSH_SECRET_KEY=replace-with-a-long-random-secret
```

`WALISSH_SECRET_KEY` 用于加密 SSH 密码和私钥。生产环境必须使用足够长的随机值，并通过部署系统的 Secret 机制注入，不能提交到仓库。

## 本地启动

```bash
python -m pip install -e '.[test]'
uvicorn app.main:app --host 0.0.0.0 --port 8090
```

启动后可访问：

- OpenAPI：`http://127.0.0.1:8090/docs`
- Agent 列表：`GET /api/v1/query_ai_agent_config_list`
- 创建会话：`POST /api/v1/create_session`
- 同步聊天：`POST /api/v1/chat`
- 流式聊天：`POST /api/v1/chat_stream`

`chat_stream` 返回每行一个 JSON 对象的 NDJSON，不使用 `data:` SSE 帧。

## Docker

```bash
docker build -t walissh-python .
docker run --rm -p 8090:8090 --env-file .env walissh-python
```

也可以使用 `docs/dev-ops/docker-compose-app.yml` 启动服务。

## 安全边界

- Agent 不具备本机命令执行工具。
- `executeCommand` 只能操作当前聊天会话绑定的远程 PTY。
- 未绑定终端时，命令调用会被拒绝。
- 高风险命令必须在当前用户消息中包含明确确认。
- 模型调用、SSH 连接和终端会话使用不同的标识与生命周期。
- 浏览器终端输出与 Agent 命令捕获使用独立缓冲区。
- 模型循环具有步骤、工具次数和超时上限。

## 测试

```bash
pytest -q
python -m compileall -q app tests
git diff --check
```

外部集成验收还需要可访问的 MySQL、DeepSeek API 和测试 SSH 主机。详细兼容范围与生产验收条件见：

- `API_COMPATIBILITY_MATRIX.md`
- `FEATURE_INVENTORY.md`
- `IMPLEMENTATION_MAPPING.md`
- `AUTOMATION_READINESS.md`
- `COMPATIBILITY_QUIRKS.md`
