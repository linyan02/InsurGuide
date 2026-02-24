# InsurGuide - 智保灵犀智能保险指南系统

基于 FastAPI、LangChain 与 RAGflow 的**智能保险指南与增强 RAG 系统**，支持 PC Web、Gradio 演示与小程序复用 API。实现多轮对话、意图识别、问题改写、知识库检索（RAGflow）、答案生成与合规校验，以及交互/合规日志落库。

> **架构说明**：[doc/架构说明.md](doc/架构说明.md)  
> **项目说明**：[doc/项目说明.md](doc/项目说明.md)  
> **中间件与安装**：[README_MIDDLEWARE.md](README_MIDDLEWARE.md)  
> **详细技术实现**：[doc/详细技术实现方案.md](doc/详细技术实现方案.md)  
> **阿里云 ECS Docker 部署**：[doc/Docker部署说明-阿里云ECS.md](doc/Docker部署说明-阿里云ECS.md)

## 项目特性

- **FastAPI**：现代化 Python Web 框架，提供 REST API 与 OpenAPI 文档
- **增强 RAG 流水线**：意图识别（rule/llm/llm_vector/bert）→ 问题改写 → RAGflow 召回 → 答案生成 → 合规校验
- **多轮对话**：Redis 存储对话上下文，支持历史记录与上下文恢复
- **双模型方案**：专业版（qwen-plus）/ 标准版（qwen-turbo），可按请求选择
- **合规与审计**：违规词屏蔽、交互日志与合规日志写入 MySQL
- **用户认证**：JWT 登录/注册，支持 `/api/auth/me`、对话历史等鉴权接口
- **数据与检索**：MySQL（用户与日志）、Redis（上下文）、RAGflow（主知识库）、ChromaDB（意图/改写规则）、Elasticsearch（可选）
- **前端**：PC Web 单页（`web/static`）、Gradio 演示（`gradio_ui`），API 可复用于小程序

## 快速开始

### 环境要求

- Python 3.9+
- MySQL 5.7+ 或 8.0+
- Redis（多轮对话上下文，必选）
- RAGflow 服务（知识库检索，必选）
- Elasticsearch 7.0+（可选）

### 安装步骤

1. **克隆并进入项目**

```bash
cd InsurGuide
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

复制 `.env.example` 为 `.env` 并按需修改：

```bash
cp .env.example .env
```

主要配置项示例：

```env
# MySQL（用户、交互日志、合规日志）
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=insurguide

# Redis（多轮对话上下文，必选）
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

# RAGflow（知识库检索，必选）
RAGFLOW_API_URL=http://your-ragflow-host:9380/api/v1
RAGFLOW_API_KEY=your-ragflow-api-key
RAGFLOW_KNOWLEDGE_BASE_ID=your-knowledge-base-id

# JWT（生产环境请修改 SECRET_KEY）
SECRET_KEY=your-secret-key-change-this-in-production

# 大模型（通义千问等，用于答案生成/意图/改写）
DASHSCOPE_API_KEY=your-dashscope-api-key

# 意图/改写模式：rule | llm | llm_vector（bert 需单独配置）
INTENT_MODE=rule
REWRITE_MODE=rule
```

5. **创建数据库**

在 MySQL 中执行：

```sql
CREATE DATABASE insurguide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **启动应用**

**启动 API 服务（供 PC Web / Gradio / 小程序调用）：**

```bash
python main.py
```

或指定 host/port：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- API 文档：http://localhost:8000/docs  
- PC Web 单页：http://localhost:8000/static/index.html（需先启动 API）

**启动 Gradio 演示 UI：**

```bash
python gradio_app.py
```

访问：http://localhost:7860（需先启动后端 API：`python main.py`）

## 项目结构

```
InsurGuide/
├── doc/                      # 项目与架构文档
│   ├── 架构说明.md
│   ├── 项目说明.md
│   ├── 项目架构说明.md
│   ├── 详细技术实现方案.md
│   ├── RAGflow调用链路.md
│   └── 保险知识/              # 知识库文档
├── config/                   # 配置层
│   ├── settings.py           # 统一配置（.env）
│   └── constants.py          # 常量
├── core/                     # 核心基础设施层
│   ├── database.py           # MySQL
│   ├── redis_store.py        # 对话上下文（Redis）
│   ├── vector_db.py          # ChromaDB
│   ├── es_client.py          # Elasticsearch
│   └── auth.py               # JWT 认证
├── services/                 # 增强 RAG 服务层
│   └── rag/
│       ├── pipeline.py       # 流水线编排（意图→改写→召回→答案→合规）
│       ├── langchain_chain.py # LangChain 编排（USE_LANGCHAIN_RAG 时使用）
│       ├── recall.py         # 召回层
│       ├── fusion.py         # 融合层
│       ├── rerank.py         # 精排层
│       ├── _ragflow.py       # RAGflow 调用
│       └── langchain_*.py    # LangChain RAGflow/LLM 封装
├── api/                      # API 入口
│   └── main.py               # FastAPI 应用、路由注册、静态资源挂载
├── routers/                  # API 路由
│   ├── auth.py               # 认证（注册/登录/me）
│   ├── chat.py               # 增强 RAG 对话（/api/chat、history、context/restore）
│   ├── vector.py             # 向量库
│   ├── es.py                 # Elasticsearch
│   └── intent_rewrite_rules.py # 意图/改写规则管理
├── app/                      # 业务实现（意图/改写/答案/合规/RAGflow 等）
│   ├── intent.py             # 意图识别
│   ├── query_rewrite.py      # 问题改写
│   ├── chat_service.py       # 对话编排（与 pipeline 并行实现）
│   ├── answer_engine.py      # 答案生成
│   ├── compliance.py        # 合规校验与屏蔽
│   ├── ragflow_client.py    # RAGflow 检索客户端
│   ├── model_plan.py        # 专业版/标准版模型选择
│   ├── context_store.py     # 上下文存取（兼容）
│   └── ...
├── models/                   # ORM 模型（用户、交互日志、合规日志）
├── web/                      # PC Web 前端
│   └── static/               # 静态资源（如 index.html）
├── gradio_ui/                # Gradio 演示前端（模块化 Tab 页）
│   ├── app.py
│   ├── config.py
│   ├── pages/                # 认证、对话、RAG、向量、ES 等
│   └── components/
├── tests/                    # 测试（API、RAG、合规、配置等）
├── main.py                   # 统一启动入口（启动 api.main:app）
├── gradio_app.py             # Gradio 演示入口
├── requirements.txt
├── .env.example
└── README.md
```

## 配置说明

- **MySQL**：存储用户、`interaction_logs`、`compliance_logs`，需先建库。
- **Redis**：存储多轮对话上下文，`/api/chat` 与 `/api/chat/clear` 依赖 Redis。
- **RAGflow**：主知识库检索，需配置 `RAGFLOW_API_URL`、`RAGFLOW_API_KEY`、`RAGFLOW_KNOWLEDGE_BASE_ID`。
- **意图/改写**：`INTENT_MODE` / `REWRITE_MODE` 可选 `rule`、`llm`、`llm_vector`；BERT 模式需配置 `BERT_INTENT_*`。
- **增强 RAG 模式**：`USE_LANGCHAIN_RAG=True` 时使用 LangChain 编排（RAGflowRetriever + DashScopeLLM），否则使用 `services.rag.pipeline`。
- **向量库**：ChromaDB 用于意图/改写规则等，数据目录由 `VECTOR_DB_PATH` 指定。

更多中间件安装与配置见 [README_MIDDLEWARE.md](README_MIDDLEWARE.md)。

## API 文档

启动服务后可访问：

- Swagger UI：http://localhost:8000/docs  
- ReDoc：http://localhost:8000/redoc  

### 主要接口

| 类型 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 认证 | POST | `/api/auth/register` | 用户注册 |
| 认证 | POST | `/api/auth/login` | 用户登录 |
| 认证 | GET | `/api/auth/me` | 获取当前用户（需 Bearer Token） |
| 对话 | POST | `/api/chat` | 多轮对话（body: `user_id`, `query`，可选 `intent_mode`, `rewrite_mode`, `model_plan`） |
| 对话 | POST | `/api/chat/clear` | 清除指定用户对话上下文 |
| 对话 | GET | `/api/chat/history` | 当前用户最近对话记录（需登录） |
| 对话 | GET | `/api/chat/history/{log_id}` | 单条记录详情（需登录） |
| 对话 | POST | `/api/chat/context/restore` | 从某条历史恢复上下文（需登录） |
| 规则 | POST | `/api/intent-rules/add` | 添加意图规则 |
| 规则 | POST | `/api/rewrite-rules/add` | 添加改写规则 |
| 向量 | POST | `/api/vector/add` | 添加文档到向量库 |
| 向量 | POST | `/api/vector/query` | 向量检索 |
| 向量 | DELETE | `/api/vector/delete` | 删除向量文档 |
| ES | POST | `/api/es/index` | 索引文档 |
| ES | POST | `/api/es/search` | 搜索 |
| ES | POST | `/api/es/create-index` | 创建索引 |
| ES | DELETE | `/api/es/delete-index/{index_name}` | 删除索引 |
| ES | GET | `/api/es/health` | ES 健康检查 |

## 使用示例

### 多轮对话

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user001", "query": "百万医疗能报多少？", "model_plan": "standard"}'
```

### 用户登录

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123"
```

### 清除对话上下文

```bash
curl -X POST "http://localhost:8000/api/chat/clear" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user001"}'
```

更多示例见 [doc/手工验收CheckList.md](doc/手工验收CheckList.md)。

## 安全说明

1. **生产环境**：修改 `SECRET_KEY`、关闭 `DEBUG`、配置 CORS、使用 HTTPS。  
2. **数据库**：使用强密码、限制访问 IP、定期备份。  
3. **API**：需认证接口请携带 `Authorization: Bearer <token>`。

## 开发

### 运行测试

```bash
pytest tests/ -v
pytest tests/ -v --cov=config --cov=core --cov=services --cov=app --cov-report=term-missing
```

说明见 [tests/README.md](tests/README.md)。

### 代码风格

```bash
pip install black flake8
black .
flake8 .
```

## 依赖概览

见 `requirements.txt`，主要包括：

- FastAPI ≥0.115.0、uvicorn 0.24.0、pydantic-settings
- LangChain、langchain-community、langchain-openai、langchain-core
- Gradio 4.7.1
- SQLAlchemy 2.0.23、pymysql、Redis 5.0.1
- ChromaDB 0.4.18、sentence-transformers、faiss-cpu
- Elasticsearch 8.11.0
- python-jose、passlib、bcrypt、python-dotenv
- pytest、pytest-cov

## 贡献与许可

欢迎提交 Issue 和 Pull Request。  
本项目采用 MIT License。  
如有问题或建议，请提交 Issue。

---

**注意**：本项目仅用于学习与开发，生产使用前请做好安全与合规评估。
