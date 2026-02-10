# InsurGuide - 智能保险指南系统

基于 FastAPI、LangChain 和 Gradio 构建的智能保险指南平台，支持 Web 端登录、MySQL 数据库、向量数据库和 Elasticsearch 搜索。并实现**智保灵犀增强 RAG 调用系统**（多轮对话、意图识别、问题改写、召回/融合/精排、合规校验、交互/合规日志）。

> **架构说明**：[doc/架构说明.md](doc/架构说明.md)  
> **项目说明**：[doc/项目说明.md](doc/项目说明.md)  
> **中间件与安装**：[README_MIDDLEWARE.md](README_MIDDLEWARE.md)  
> **详细技术实现**：[doc/详细技术实现方案.md](doc/详细技术实现方案.md)

## 📋 项目特性

- ✅ **FastAPI** - 现代化的 Python Web 框架，提供高性能的 API 服务
- ✅ **LangChain** - 集成大语言模型，提供智能对话功能
- ✅ **Gradio** - 友好的 Web UI 界面
- ✅ **用户认证** - 基于 JWT 的用户登录和注册系统
- ✅ **MySQL 数据库** - 关系型数据库支持
- ✅ **向量数据库** - 基于 ChromaDB 的向量存储和检索
- ✅ **Elasticsearch** - 全文搜索和数据分析

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MySQL 5.7+ 或 MySQL 8.0+
- Elasticsearch 7.0+ (可选)
- OpenAI API Key (可选，用于 LangChain)

### 安装步骤

1. **克隆项目**

```bash
cd InsurGuide
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置以下内容：

```env
# MySQL 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=insurguide

# Elasticsearch 配置
ES_HOST=localhost
ES_PORT=9200

# JWT 密钥（生产环境请修改）
SECRET_KEY=your-secret-key-change-this-in-production

# OpenAI API Key (可选)
OPENAI_API_KEY=your-openai-api-key-here
```

5. **创建数据库**

在 MySQL 中创建数据库：

```sql
CREATE DATABASE insurguide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

6. **初始化数据库表**

运行应用会自动创建数据库表，或手动运行：

```python
from app.database import Base, engine
Base.metadata.create_all(bind=engine)
```

7. **启动应用**

**启动 API 服务（供 PC Web / 小程序调用）：**

```bash
python main.py
```

或：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

- API 文档：http://localhost:8000/docs  
- PC Web 单页：http://localhost:8000/static/index.html（需先启动 API）

**启动 Gradio 演示 UI：**

```bash
python gradio_app.py
```

访问：http://localhost:7860

## 📁 项目结构（分层架构）

```
InsurGuide/
├── doc/                    # 项目与架构文档
│   ├── 架构说明.md
│   ├── 项目说明.md
│   ├── 详细技术实现方案.md
│   └── 智保灵犀增强RAG调用系统产品技术方案.pdf
├── config/                 # 配置层
│   ├── settings.py        # 统一配置（.env）
│   └── constants.py       # 常量
├── core/                   # 核心基础设施层
│   ├── database.py        # MySQL
│   ├── redis_store.py     # 对话上下文
│   ├── vector_db.py       # ChromaDB
│   ├── es_client.py       # Elasticsearch
│   └── auth.py            # JWT 认证
├── services/               # 增强 RAG 服务层
│   └── rag/               # 意图→改写→召回→融合→精排→流水线
│       ├── recall.py      # 召回层
│       ├── fusion.py      # 融合层
│       ├── rerank.py      # 精排层
│       ├── pipeline.py    # 流水线编排
│       └── _ragflow.py    # RAGflow 调用
├── api/                    # API 接口服务层（供 Web/小程序）
│   └── main.py            # FastAPI 应用入口
├── web/                    # PC Web 前端模块
│   ├── static/            # 静态资源（如 index.html）
│   └── README.md
├── routers/                # API 路由（认证/对话/向量/ES/规则）
├── app/                    # 业务实现（意图/改写/答案/合规等，兼容层）
├── models/                 # ORM 模型
├── tests/                  # 测试模块
│   ├── conftest.py        # pytest fixture（TestClient、测试 DB）
│   ├── test_api_health.py # 健康/根路径
│   ├── test_api_auth.py   # 认证 API
│   ├── test_api_chat.py   # 对话 API
│   ├── test_services_rag.py # 融合/精排单元测试
│   ├── test_app_compliance.py # 合规单元测试
│   └── test_config.py     # 配置与常量
├── utils/
├── config.py              # 配置入口（兼容）
├── main.py                # 统一启动入口（启动 api.main:app）
├── gradio_app.py          # Gradio 演示 UI
├── requirements.txt
├── .env.example
└── README.md
```

## 🔧 配置说明

### MySQL 配置

确保 MySQL 服务正在运行，并在 `.env` 文件中配置正确的连接信息。

### Elasticsearch 配置

如果使用 Elasticsearch，确保服务正在运行。可以通过以下命令检查：

```bash
curl http://localhost:9200
```

### 向量数据库配置

项目使用 ChromaDB 作为向量数据库，数据会存储在 `./vector_db` 目录中（可在 `.env` 中配置）。

## 📚 API 文档

启动 FastAPI 服务后，可以访问以下地址查看 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 主要 API 端点

#### 认证相关

- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `GET /api/auth/me` - 获取当前用户信息

#### 向量数据库相关

- `POST /api/vector/add` - 添加文档到向量数据库
- `POST /api/vector/query` - 查询向量数据库
- `DELETE /api/vector/delete` - 删除向量数据库中的文档

#### 增强 RAG 对话（智保灵犀）

- `POST /api/chat` - 多轮对话（Body: `user_id`, `query`，返回答案与溯源来源）
- `POST /api/chat/clear` - 清除指定用户的对话上下文

#### Elasticsearch 相关

- `POST /api/es/index` - 索引文档到 Elasticsearch
- `POST /api/es/search` - 搜索文档
- `POST /api/es/create-index` - 创建索引
- `DELETE /api/es/delete-index/{index_name}` - 删除索引
- `GET /api/es/health` - 获取 Elasticsearch 健康状态

## 🎯 使用示例

### 1. 用户注册

```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

### 2. 用户登录

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123"
```

### 3. 添加文档到向量数据库

```bash
curl -X POST "http://localhost:8000/api/vector/add" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": ["这是第一个文档", "这是第二个文档"],
    "metadatas": [{"source": "doc1"}, {"source": "doc2"}]
  }'
```

### 4. 查询向量数据库

```bash
curl -X POST "http://localhost:8000/api/vector/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query_texts": ["查询内容"],
    "n_results": 5
  }'
```

### 5. 搜索 Elasticsearch

```bash
curl -X POST "http://localhost:8000/api/es/search" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "index": "insurguide",
    "query": {
      "match": {
        "_all": "搜索关键词"
      }
    }
  }'
```

## 🔐 安全说明

1. **生产环境配置**：
   - 修改 `SECRET_KEY` 为强随机字符串
   - 设置 `DEBUG=False`
   - 配置正确的 CORS 允许域名
   - 使用 HTTPS

2. **数据库安全**：
   - 使用强密码
   - 限制数据库访问 IP
   - 定期备份数据

3. **API 安全**：
   - 所有需要认证的 API 都需要 Bearer Token
   - Token 有过期时间，默认 30 分钟

## 🛠️ 开发

### 运行测试

```bash
# 安装依赖后执行
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=config --cov=core --cov=services --cov=app --cov-report=term-missing
```

测试模块说明见 [tests/README.md](tests/README.md)。

### 运行开发服务器

```bash
# FastAPI (支持热重载)
uvicorn main:app --reload

# Gradio
python gradio_app.py
```

### 代码风格

建议使用以下工具保持代码风格一致：

```bash
pip install black flake8
black .
flake8 .
```

## 📦 依赖版本

详见 `requirements.txt` 文件，主要依赖包括：

- FastAPI 0.104.1
- LangChain 0.1.0
- Gradio 4.7.1
- SQLAlchemy 2.0.23
- Elasticsearch 8.11.0
- ChromaDB 0.4.18

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请提交 Issue。

---

**注意**：本项目仅用于学习和开发目的，生产环境使用前请进行充分的安全评估和测试。
