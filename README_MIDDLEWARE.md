# 智保灵犀增强 RAG 系统 - 中间件与本地安装说明

本项目运行依赖以下中间件与服务。按「必选」与「可选」区分，并给出本地安装方法。

---

## 一、必选中间件

### 1. Python 环境

- **版本**：Python 3.9+
- **建议**：使用 venv 或 conda 隔离环境。

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

---

### 2. MySQL

- **用途**：用户数据、交互日志（interaction_logs）、合规日志（compliance_logs）。
- **版本**：MySQL 5.7+ 或 8.0+。

#### 本地安装（macOS）

```bash
# Homebrew
brew install mysql
brew services start mysql

# 创建数据库与用户（按需修改）
mysql -u root -e "CREATE DATABASE insurguide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### 本地安装（Ubuntu/Debian）

```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo mysql -e "CREATE DATABASE insurguide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

#### 配置

在项目根目录复制 `.env.example` 为 `.env`，填写：

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=insurguide
```

应用启动时会自动创建表（含 `users`、`interaction_logs`、`compliance_logs` 等）。

---

### 3. Redis

- **用途**：多轮对话上下文缓存（Key：用户 ID，Value：最近 N 轮对话，TTL 30 分钟）。
- **版本**：Redis 6.0+，推荐 7.0。

#### 本地安装（macOS）

```bash
brew install redis
brew services start redis
# 或前台运行：redis-server
```

#### 本地安装（Ubuntu/Debian）

```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

#### Docker 方式（与产品文档一致）

```bash
docker run -d --name redis -p 6379:6379 --memory=2g redis:7.0 --maxmemory 2gb --maxmemory-policy allkeys-lru
```

#### 配置

在 `.env` 中：

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # 无密码留空
REDIS_CONTEXT_TTL_MINUTES=30
REDIS_MAX_HISTORY_TURNS=10
```

---

### 4. RAGflow（知识库检索）

- **用途**：文档解析、向量化、检索；增强 RAG 服务通过 HTTP 调用其检索 API。
- **部署**：独立部署（可与本服务同机或异机），推荐 Docker Compose。

#### 本地安装（Docker Compose）

```bash
# 1. 克隆 RAGflow
git clone https://github.com/infiniflow/ragflow.git
cd ragflow

# 2. 按需修改 docker-compose.yml 资源限制（如 2 核 8G 机器）
# 例如：ragflow-api 的 memory 限制为 4G

# 3. 启动
docker-compose up -d

# 4. 访问后台：http://localhost:9380（或 9000，视版本而定）
# 默认账号：admin@ragflow.com / 123456（请查阅官方文档确认）
```

在 RAGflow 后台中：

- 创建知识库（如「重疾险知识库」），上传 PDF/Word 等；
- 开启智能分块、配置向量模型（如 bge-large-zh-v1.5）；
- 在「设置 - API 管理」中生成 API Key；
- 记录知识库 ID（或 Chat ID，视所用 API 而定）。

#### 配置

在 `.env` 中填写 RAGflow 的地址与密钥：

```env
RAGFLOW_API_URL=http://localhost:9380/v1/search
RAGFLOW_API_KEY=生成的API密钥
RAGFLOW_KNOWLEDGE_BASE_ID=知识库或 Chat ID
RAGFLOW_TOP_K=3
RAGFLOW_TIMEOUT=10
```

若 RAGflow 实际提供的检索接口路径不同，请将 `RAGFLOW_API_URL` 改为实际 POST 检索地址。

---

### 5. 大模型 API（答案生成）

增强 RAG 使用「知识库检索结果 + 历史上下文 + Prompt」生成答案，需任选其一：

- **通义千问（推荐）**：在 [阿里云 DashScope](https://dashscope.aliyun.com/) 开通并获取 API Key。
- **OpenAI 兼容**：填写 `OPENAI_API_KEY`，使用 OpenAI 或兼容该接口的服务。

#### 配置

```env
LLM_MODE=api
DASHSCOPE_API_KEY=你的通义千问Key
# 或
OPENAI_API_KEY=你的OpenAI或兼容接口Key
```

若不配置任何 API Key，接口仍可运行，但会返回兜底提示（建议配置 API 以正常生成答案）。

---

## 二、可选中间件

### 1. Elasticsearch

- **用途**：全文检索、数据分析（现有 `/api/es/*` 接口）。
- **版本**：7.x 或 8.x。

#### 本地安装（Docker）

```bash
docker run -d --name es -p 9200:9200 -e "discovery.type=single-node" -e "xpack.security.enabled=false" elasticsearch:8.11.0
```

在 `.env` 中配置 `ES_HOST`、`ES_PORT` 等；未配置或未启动时，ES 相关接口会报错，不影响 `/api/chat`。

---

### 2. 向量数据库（ChromaDB）

- **用途**：项目内向量检索（`/api/vector/*`），与 RAGflow 独立。
- **说明**：ChromaDB 为 Python 内嵌，数据存于本地目录，无需单独安装服务。
- **配置**：`.env` 中 `VECTOR_DB_PATH`、`VECTOR_DB_COLLECTION`。

---

### 3. 本地小模型（Qwen-1.8B）

- **用途**：无 GPU 时可用 CPU 推理生成答案（较慢）。
- **说明**：需安装 `transformers`、`torch` 等，并下载模型，仅当 `LLM_MODE=local` 时使用。

```env
LLM_MODE=local
```

不配置则使用 `api` 模式（通义/OpenAI）。

---

## 三、合规词库（无需单独安装）

违规词在配置中维护，通过环境变量动态生效：

```env
VIOLATION_WORDS=保证赔付,100%理赔,无风险,稳赚,必赔
```

修改后重启应用即可，无需重启中间件。

---

## 四、启动前检查清单

| 中间件     | 必选/可选 | 默认端口 | 检查命令示例           |
|------------|-----------|----------|------------------------|
| Python 3.9+ | 必选      | -        | `python --version`     |
| MySQL      | 必选      | 3306     | `mysql -u root -p -e "SELECT 1"` |
| Redis      | 必选（chat） | 6379  | `redis-cli ping`       |
| RAGflow    | 必选（chat） | 9380/9000 | `curl -s http://localhost:9380` |
| 大模型 API | 必选（正常答案） | -   | 在 .env 配置 Key       |
| Elasticsearch | 可选   | 9200     | `curl http://localhost:9200`     |

---

## 五、启动应用

```bash
# 1. 复制环境变量
cp .env.example .env
# 编辑 .env 填写上述各项

# 2. 启动 FastAPI（增强 RAG 主服务）
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

# 3. 可选：启动 Gradio Web UI
python gradio_app.py
```

- API 文档：http://localhost:8000/docs  
- 多轮对话接口：`POST /api/chat`（Body: `{"user_id":"xxx","query":"重疾险等待期多久"}`）

---

## 六、生产部署注意

- 生产环境请修改 `SECRET_KEY`、数据库与 Redis 密码，并限制 CORS 与访问 IP。
- RAGflow、Redis 建议与应用同网段或通过内网访问，避免将 API Key 暴露到公网。
- 日志与合规数据保留策略可在业务层按需做归档或清理（如保留 30 天）。

以上为项目运行所需中间件及本地安装方法，与 `doc/` 下产品技术方案一致。
