# InsurGuide 阿里云 ECS Docker 部署说明

本文说明在**阿里云 ECS** 上使用 Docker 部署 InsurGuide API 服务。假设 **MySQL、Redis、RAGflow 等中间件已在 ECS 或云上部署完成**，只需部署应用容器并正确连接这些服务。

---

## 一、前置条件

- 阿里云 ECS 已安装 Docker（`docker --version` 可用）
- 中间件已就绪并可访问：
  - **MySQL**：用于用户、交互日志、合规日志
  - **Redis**：用于多轮对话上下文
  - **RAGflow**：知识库检索（需可被 ECS 访问的 URL 与 API Key）
- 通义千问等大模型 API Key 已准备（`DASHSCOPE_API_KEY`）

---

## 二、获取代码（从 Git 拉取）

在 ECS 上先拉取项目代码，再基于该目录构建镜像。例如：

```bash
# 选一个你放项目的目录，如 /opt 或 /home/ubuntu
cd /opt
git clone https://github.com/你的用户名/InsurGuide.git
cd InsurGuide
# 若使用 SSH：git clone git@github.com:你的用户名/InsurGuide.git
```

若仓库是私有的，需在 ECS 上配置 Git 认证（SSH 密钥或 HTTPS 凭据）。拉取后确认当前目录下有 `Dockerfile`、`requirements.txt` 再继续下一步。

---

## 三、构建镜像

在项目根目录（含 `Dockerfile`、`requirements.txt`）执行：

```bash
cd /path/to/InsurGuide   # 即上一步 clone 后的目录
docker build -t insurguide:latest .
```

若需使用国内 pip 源加速（Dockerfile 已内置清华源），构建即可。如需自定义镜像名：

```bash
docker build -t your-registry.cn-hangzhou.aliyuncs.com/your-ns/insurguide:v1.0 .
```

---

## 四、配置环境变量（连接已有中间件）

容器通过**环境变量**连接 MySQL、Redis、RAGflow。请按实际中间件地址填写。

### 方式 A：使用 env 文件（推荐）

在 ECS 上创建 `.env.production`（不要提交到 Git）：

```env
# 应用
DEBUG=False
SECRET_KEY=请替换为足够随机的生产密钥

# MySQL（改为你的 RDS 或 ECS 本机地址）
MYSQL_HOST=rm-xxxxx.mysql.rds.aliyuncs.com
MYSQL_PORT=3306
MYSQL_USER=insurguide
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=insurguide

# Redis（改为你的云 Redis 或 ECS 本机地址）
REDIS_HOST=r-xxxxx.redis.rds.aliyuncs.com
REDIS_PORT=6379
REDIS_PASSWORD=你的Redis密码

# RAGflow（改为你实际部署的 RAGflow 地址）
RAGFLOW_API_URL=http://你的RAGflow主机:9380/api/v1
RAGFLOW_API_KEY=你的RAGflow-API-Key
RAGFLOW_KNOWLEDGE_BASE_ID=你的知识库ID

# 大模型
DASHSCOPE_API_KEY=你的通义千问Key
LLM_MODE=api

# 意图/改写（可选，默认 rule）
INTENT_MODE=rule
REWRITE_MODE=rule
```

**若 MySQL/Redis 部署在 ECS 本机**：

- 使用 `host.docker.internal`（Docker 20.10+，仅部分 Linux 支持），或  
- 使用宿主机内网 IP（如 `172.17.0.1` 或 `ifconfig` 看到的内网 IP），例如：  
  `MYSQL_HOST=172.17.0.1`、`REDIS_HOST=172.17.0.1`

### 方式 B：命令行传参

不建文件时，可用 `-e` 传递关键变量：

```bash
docker run -d --name insurguide -p 8000:8000 \
  -e DEBUG=False \
  -e MYSQL_HOST=你的MySQL地址 \
  -e MYSQL_PASSWORD=xxx \
  -e REDIS_HOST=你的Redis地址 \
  -e REDIS_PASSWORD=xxx \
  -e RAGFLOW_API_URL=http://你的RAGflow:9380/api/v1 \
  -e RAGFLOW_API_KEY=xxx \
  -e RAGFLOW_KNOWLEDGE_BASE_ID=xxx \
  -e DASHSCOPE_API_KEY=xxx \
  -e SECRET_KEY=你的JWT密钥 \
  insurguide:latest
```

---

## 五、运行容器

使用 env 文件启动（推荐）：

```bash
docker run -d \
  --name insurguide \
  -p 8000:8000 \
  --env-file .env.production \
  --restart unless-stopped \
  insurguide:latest
```

- `-p 8000:8000`：宿主机 8000 映射容器 8000  
- `--restart unless-stopped`：宿主机重启后容器自动拉起  

查看日志：

```bash
docker logs -f insurguide
```

---

## 六、阿里云 ECS 安全组

在 ECS 控制台为实例安全组放通 **8000** 端口（入方向），以便外网或负载均衡访问 API。若仅通过 Nginx/SLB 反代，可只对 SLB 或内网开放。

---

## 七、验证部署

在 ECS 本机或同 VPC 机器执行：

```bash
curl http://localhost:8000/health
# 期望：{"status":"healthy"}

curl http://localhost:8000/
# 期望：欢迎信息与 docs 等链接
```

浏览器访问：`http://你的ECS公网IP:8000/docs` 查看 Swagger 文档。

---

## 八、可选：使用 docker-compose

若希望用 compose 管理单容器 + env 文件，可在项目根目录创建 `docker-compose.yml`：

```yaml
# 仅编排应用，中间件由 ECS/云服务提供
services:
  app:
    image: insurguide:latest
    container_name: insurguide
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    restart: unless-stopped
```

启动：

```bash
docker compose up -d
```

---

## 九、一键部署（后续更新）

首次安装部署完成后，之后每次只需**拉取最新代码并执行一条命令**即可完成部署。

### 使用部署脚本（推荐）

项目已提供 `scripts/deploy.sh`，会依次执行：`git pull` → 构建镜像 → 停止旧容器 → 启动新容器。

在 ECS 上，进入项目根目录后执行：

```bash
cd /path/to/InsurGuide
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

脚本会使用当前目录下的 `.env.production`；若环境变量文件不在项目根目录，可指定：

```bash
ENV_FILE=/opt/insurguide.env ./scripts/deploy.sh
```

可选变量：`IMAGE_NAME`（默认 `insurguide:latest`）、`CONTAINER_NAME`（默认 `insurguide`）、`PORT`（默认 `8000`）。

### 手动更新步骤

若不想用脚本，可手动执行：

```bash
cd /path/to/InsurGuide
git pull
docker build -t insurguide:latest .
docker stop insurguide && docker rm insurguide
docker run -d --name insurguide -p 8000:8000 --env-file .env.production --restart unless-stopped insurguide:latest
```

---

## 十、回滚

若新版本有问题，可用旧镜像重新运行容器（部署前可先 `docker tag` 保留当前版本）：

```bash
# 例：保留当前镜像为 old，再拉代码用新镜像部署；出问题时用 old 回滚
docker tag insurguide:latest insurguide:old
# 回滚时：
docker stop insurguide && docker rm insurguide
docker run -d --name insurguide -p 8000:8000 --env-file .env.production --restart unless-stopped insurguide:old
```

---

## 十一、常见问题

| 现象 | 处理 |
|------|------|
| 容器内连不上 MySQL/Redis | 检查 ECS 安全组、RDS/Redis 白名单是否放通 ECS 内网 IP；若中间件在本机，用宿主机内网 IP 或 `host.docker.internal`（如可用） |
| RAGflow 超时 | 确认 `RAGFLOW_API_URL` 可从容器访问（同 VPC 或公网），并检查 RAGflow 服务与 `RAGFLOW_API_KEY`、知识库 ID |
| 健康检查 200 但对话 500 | 查看 `docker logs insurguide`，重点看 MySQL/Redis/RAGflow 连接与 DASHSCOPE_API_KEY 是否配置 |
| 需要持久化向量库 | 若使用 ChromaDB 持久化，可加挂载：`-v /data/insurguide/vector_db:/app/vector_db`，并设置 `VECTOR_DB_PATH=/app/vector_db` |

按上述步骤即可在阿里云 ECS 上仅部署应用代码，中间件继续使用已有 MySQL、Redis、RAGflow 等。
