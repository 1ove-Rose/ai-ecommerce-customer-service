# Smart CS Multi-Agent 电商客服系统

基于 FastAPI、LangGraph、MCP、PostgreSQL、Redis、FAISS 和 Next.js 的电商客服多 Agent 工作台。

## 架构边界

系统固定四个子 Agent：

- `IntentRouterAgent`：识别电商客服意图并路由。
- `KnowledgeRAGAgent`：处理商品 FAQ、售后政策、发票、会员、物流时效等知识问答。
- `TicketHandlerAgent`：编排订单、物流、售后、投诉、转人工等事务动作。
- `ComplianceCheckerAgent`：最终回复质检、隐私脱敏、越权承诺检查。

订单、物流、售后、工单、知识库和用户画像能力通过 MCP 工具进入服务层，Agent 不直接访问数据库。

## 本地依赖

需要本地已有：

- Python 3.12+
- PostgreSQL，默认 `postgres / 123456 / 5432`
- Redis，默认 `localhost:6379`
- Node.js，用于 Next.js 前端

RAG 使用本地方案：

- 本地向量模型：`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- 本地向量库：`faiss-cpu`

首次运行本地向量模型会下载模型文件。如果暂时无法下载或未安装 `sentence-transformers`，系统会降级到轻量关键词向量检索，后端不会因此无法启动。

## 环境变量

复制模板：

```powershell
copy .env.example .env
```

关键配置：

```env
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-chat
DATABASE_URL=postgresql+asyncpg://postgres:123456@127.0.0.1:5432/smartcs
REDIS_URL=redis://localhost:6379/0
KNOWLEDGE_BASE_DIR=./knowledge_base
FAISS_INDEX_PATH=./vector_store/faiss_index
EMBEDDING_BACKEND=sentence_transformers
LOCAL_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

不要提交 `.env`。

## 安装后端依赖

```powershell
pip install -r requirements.txt
```

如果只想先跑通主流程，但暂时不安装本地向量模型，可以先确保 `faiss-cpu`、`numpy` 已安装。完整 RAG 推荐安装全部依赖。

## 初始化 PostgreSQL

创建数据库：

```powershell
python -c "import asyncio, asyncpg; loop=asyncio.new_event_loop(); asyncio.set_event_loop(loop); conn=loop.run_until_complete(asyncpg.connect(user='postgres', password='123456', host='127.0.0.1', port=5432, database='postgres')); exists=loop.run_until_complete(conn.fetchval('select 1 from pg_database where datname=`$1', 'smartcs')); loop.run_until_complete(conn.execute('create database smartcs')) if not exists else None; print('smartcs exists' if exists else 'created smartcs'); loop.run_until_complete(conn.close())"
```

写入种子数据：

```powershell
python -m scripts.seed
```

## 启动后端

必须在项目根目录运行：

```powershell
python -m api.main
```

健康检查：

```text
http://localhost:8000/health
```

## 启动前端

```powershell
cd frontend
npm install
npm run dev
```

访问：

```text
http://localhost:3000
```

## RAG 知识库

知识库目录：

```text
knowledge_base/
├── after_sales_policy.md
├── logistics_policy.md
└── product_faq.md
```

后端启动时会读取 `KNOWLEDGE_BASE_DIR` 中的 `.md` / `.txt` 文件，分块后写入 FAISS 内存索引。若需要持久化，可调用 `LongTermMemory.save()` 或后续增加管理 API。

## MCP 工具

当前工具包括：

- `order_query`
- `order_list_by_user`
- `logistics_query`
- `after_sale_create`
- `after_sale_query`
- `ticket_create`
- `ticket_update`
- `knowledge_search`
- `user_profile_query`

工具发现：

```text
GET /api/tools
```

工具调用：

```text
POST /api/tools/call
```

## 基础测试

运行：

```powershell
pytest
```

当前测试覆盖：

- 电商意图路由规则。
- 本地 RAG 知识库加载与检索。
- Redis 短期记忆不可用时的内存回退。

## 常见问题

### 后端提示找不到 `api.main`

请确认命令在项目根目录执行：

```powershell
cd C:\Users\27295\smart-cs-multi-agent\python-impl
python -m api.main
```

### DeepSeek 认证失败

确认 `.env` 中 `OPENAI_API_KEY` 有效，并重启后端。前端不需要重启。

### Redis 旧版本报 `HELLO` 不支持

项目已固定 Redis 客户端使用 RESP2 协议，兼容旧版 Redis。

### 本地向量模型未安装

执行：

```powershell
pip install sentence-transformers faiss-cpu
```

若暂时不安装，系统会降级到轻量关键词向量检索。