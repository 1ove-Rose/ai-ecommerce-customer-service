# AI E-commerce Customer Service

面向电商售后、订单、物流和知识问答场景的多 Agent 智能客服系统。项目采用 FastAPI + LangGraph 作为后端编排层，Next.js 作为客服工作台前端，并通过 PostgreSQL、Redis、FAISS 和 MCP 工具完成业务查询、短期记忆、长期知识检索与事务处理。

## 功能概览

- 多 Agent 客服编排：意图识别、知识问答、订单/售后处理、合规检查。
- RAG 知识库：加载 `knowledge_base/` 下的商品 FAQ、物流政策和售后政策。
- MCP 工具层：统一暴露订单查询、售后创建、工单处理、知识检索等业务能力。
- 记忆能力：Redis 短期会话记忆 + FAISS 长期知识检索。
- 前端工作台：提供聊天、订单和工单页面。
- 可观测性：内置 OpenTelemetry 初始化和 Agent 指标接口。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 后端 API | FastAPI, Uvicorn, Pydantic |
| Agent 编排 | LangGraph, LangChain |
| 工具协议 | MCP |
| 数据库 | PostgreSQL, SQLAlchemy, asyncpg |
| 缓存/短期记忆 | Redis |
| 知识检索 | FAISS, sentence-transformers |
| 前端 | Next.js 15, React 19, TypeScript |
| 部署 | Docker, Docker Compose |

## 项目结构

```text
.
├── agents/              # 多 Agent 实现
├── api/                 # FastAPI 入口与 REST API
├── db/                  # 数据库模型与连接
├── frontend/            # Next.js 客服工作台
├── knowledge_base/      # RAG 知识库文档
├── mcp/                 # MCP 工具服务器
├── memory/              # 工作记忆、短期记忆、长期记忆
├── models/              # 本地 embedding 模型配置与 tokenizer 文件
├── repositories/        # 数据访问层
├── schemas/             # 业务数据结构
├── scripts/             # 初始化脚本
├── services/            # 电商业务服务层
├── tests/               # 测试用例
└── tracing/             # OpenTelemetry 配置
```

## 架构说明

```mermaid
flowchart LR
    User[用户 / 客服] --> Frontend[Next.js 工作台]
    Frontend --> API[FastAPI API]
    API --> Supervisor[LangGraph Supervisor]

    Supervisor --> Intent[IntentRouterAgent\n意图识别]
    Supervisor --> RAG[KnowledgeRAGAgent\n知识问答]
    Supervisor --> Ticket[TicketHandlerAgent\n订单/售后/工单]
    Supervisor --> Compliance[ComplianceCheckerAgent\n合规检查]

    RAG --> LongMemory[FAISS 长期知识库]
    Ticket --> MCP[MCP 工具层]
    MCP --> Service[业务服务层]
    Service --> DB[(PostgreSQL)]
    API --> Redis[(Redis 短期记忆)]
```

核心边界：

- Agent 只负责理解、编排和生成回复。
- 业务动作通过 MCP 工具进入 `services/`，Agent 不直接访问数据库。
- 数据库访问集中在 `repositories/`。
- 合规检查作为最终输出前的收口节点，负责隐私脱敏和越权承诺检查。

## 环境要求

- Python 3.12+
- Node.js 20+
- PostgreSQL 16，或使用 Docker Compose
- Redis 7，或使用 Docker Compose
- 可用的 OpenAI 兼容模型 API，例如 DeepSeek 或 OpenAI

## 环境变量

复制后端环境变量模板：

```powershell
copy .env.example .env
```

至少需要配置：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
DATABASE_URL=postgresql+asyncpg://postgres:123456@127.0.0.1:5432/smartcs
REDIS_URL=redis://localhost:6379/0
KNOWLEDGE_BASE_DIR=./knowledge_base
FAISS_INDEX_PATH=./vector_store/faiss_index
LOCAL_EMBEDDING_MODEL=./models/bge-small-zh-v1.5
```

复制前端环境变量模板：

```powershell
copy frontend\.env.local.example frontend\.env.local
```

默认配置：

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

注意：

- `.env` 和 `frontend/.env.local` 是本地敏感配置，不要提交到 GitHub。
- 仓库只保留 `.env.example` 和 `frontend/.env.local.example` 作为模板。

## 本地向量模型

本项目使用本地下载的 `bge-small-zh-v1.5` 作为 embedding 模型，默认路径为：

```text
models/bge-small-zh-v1.5
```

对应环境变量：

```env
LOCAL_EMBEDDING_MODEL=./models/bge-small-zh-v1.5
```

说明：

- `models/bge-small-zh-v1.5/` 中的配置文件和 tokenizer 文件可以保留在仓库中。
- `.bin`、`.safetensors` 等模型权重文件体积较大，已通过 `.gitignore` 排除，不会上传到 GitHub。
- 如果在新机器上运行项目，需要先把本地下载好的 `bge-small-zh-v1.5` 权重文件放回该目录，或修改 `LOCAL_EMBEDDING_MODEL` 指向实际模型路径。

## 本地启动

### 1. 安装后端依赖

```powershell
pip install -r requirements.txt
```

### 2. 准备 PostgreSQL 和 Redis

如果本机已安装 PostgreSQL 和 Redis，确保连接信息与 `.env` 一致。

也可以只启动基础设施容器：

```powershell
docker compose up -d postgres redis
```

### 3. 初始化数据库种子数据

```powershell
python -m scripts.seed
```

### 4. 启动后端

必须在项目根目录执行：

```powershell
python -m api.main
```

后端默认地址：

```text
http://localhost:8000
```

健康检查：

```text
GET http://localhost:8000/health
```

### 5. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://localhost:3000
```

## Docker Compose 启动

```powershell
docker compose up --build
```

服务端口：

- 前端：`http://localhost:3000`
- 后端：`http://localhost:8000`
- PostgreSQL：`localhost:5432`
- Redis：`localhost:6379`

如果使用 Docker Compose 运行完整后端，请确保容器环境中提供有效的 `OPENAI_API_KEY`。可以在 `docker-compose.yml` 的 `backend.environment` 中补充，或按你的部署方式注入。

## API 接口

### 聊天接口

```text
POST /api/chat
```

请求示例：

```json
{
  "message": "帮我查一下订单物流",
  "user_id": "user_001",
  "session_id": "optional-session-id"
}
```

### 会话历史

```text
GET /api/history/{session_id}
```

### MCP 工具发现

```text
GET /api/tools
```

### MCP 工具调用

```text
POST /api/tools/call
```

### 系统指标

```text
GET /api/metrics
```

### 健康检查

```text
GET /health
```

## 内置 MCP 工具

当前工具包括：

- `order_query`：查询单个订单。
- `order_list_by_user`：查询用户订单列表。
- `logistics_query`：查询物流状态。
- `after_sale_create`：创建售后申请。
- `after_sale_query`：查询售后状态。
- `ticket_create`：创建工单。
- `ticket_update`：更新工单。
- `knowledge_search`：检索知识库。
- `user_profile_query`：查询用户画像。

## RAG 知识库

默认知识库目录：

```text
knowledge_base/
├── after_sales_policy.md
├── logistics_policy.md
└── product_faq.md
```

后端启动时会读取 `KNOWLEDGE_BASE_DIR` 下的 `.md` / `.txt` 文件，并写入 FAISS 内存索引。如果知识库为空，系统会注入一条默认售后政策作为兜底知识。

## 测试

```powershell
pytest
```

当前测试覆盖：

- 电商意图路由规则。
- 本地 RAG 知识库加载与检索。
- Redis 不可用时的短期记忆回退。
- 售后和工单处理链路。

## 常见问题

### 1. DeepSeek 或 OpenAI 认证失败

检查 `.env` 中的 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`，修改后重启后端。

### 2. Redis 连接失败

确认 Redis 已启动，或使用：

```powershell
docker compose up -d redis
```

### 3. PostgreSQL 连接失败

确认数据库、用户名、密码和端口与 `DATABASE_URL` 一致。如果使用 Docker Compose，默认容器内连接为：

```env
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/smartcs
```

本地直连默认可使用：

```env
DATABASE_URL=postgresql+asyncpg://postgres:123456@127.0.0.1:5432/smartcs
```

### 4. 本地 embedding 模型缺失

项目使用本地下载的 `bge-small-zh-v1.5`，默认读取：

```text
models/bge-small-zh-v1.5
```

如果在新机器上运行项目，需要把本地模型权重文件放回该目录，或在 `.env` 中修改：

```env
LOCAL_EMBEDDING_MODEL=你的本地模型路径
```

注意：模型权重文件通常较大，`.gitignore` 已排除 `.bin`、`.safetensors` 等文件，避免上传到 GitHub。