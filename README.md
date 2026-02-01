# InsurGuide - 智能保险指南系统

基于 FastAPI、LangChain 和 Gradio 构建的智能保险指南平台，支持 Web 端登录、MySQL 数据库、向量数据库和 Elasticsearch 搜索。

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

**启动 FastAPI 服务：**

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 API 文档：http://localhost:8000/docs

**启动 Gradio Web UI：**

```bash
python gradio_app.py
```

访问 Web UI：http://localhost:7860

## 📁 项目结构

```
InsurGuide/
├── app/                    # 应用核心模块
│   ├── __init__.py
│   ├── database.py        # MySQL 数据库连接
│   ├── vector_db.py       # 向量数据库连接
│   ├── es_client.py       # Elasticsearch 客户端
│   └── auth.py            # 认证模块
├── models/                 # 数据模型
│   ├── __init__.py
│   └── user.py            # 用户模型
├── routers/                # API 路由
│   ├── __init__.py
│   ├── auth.py            # 认证路由
│   ├── vector.py          # 向量数据库路由
│   └── es.py              # Elasticsearch 路由
├── utils/                  # 工具函数
│   └── __init__.py
├── config.py              # 配置文件
├── main.py                # FastAPI 主应用
├── gradio_app.py          # Gradio Web UI
├── requirements.txt       # Python 依赖
├── .env.example           # 环境变量示例
├── .gitignore            # Git 忽略文件
└── README.md             # 项目文档
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
