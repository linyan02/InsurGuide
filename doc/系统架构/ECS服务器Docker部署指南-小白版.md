# InsurGuide 阿里云 ECS Docker 一键部署指南（运维小白版）

> 本指南面向运维新手，采用**逐步操作**的方式。  
> 项目地址：<https://github.com/linyan02/InsurGuide.git>  
> **说明**：ECS 系统自带的 Python 3.6.8 不影响部署，应用在 Docker 容器内使用 Python 3.11 运行。

---

## 一、前置准备

### 1.1 你已有/需准备的内容

| 项目 | 状态 |
|------|------|
| 阿里云 ECS 服务器 | ✅ 已有 |
| MySQL（已安装） | ✅ 已有 |
| Redis（已安装） | ✅ 已有 |
| Elasticsearch（已安装） | ✅ 已有 |
| RAGflow 服务 | ⚠️ 需单独部署或使用已有地址 |
| 通义千问 API Key | ⚠️ 需在 [DashScope 控制台](https://dashscope.console.aliyun.com/) 申请 |

### 1.2 重要说明：为什么不用管 ECS 的 Python 版本

- 项目要求 **Python 3.9+**
- ECS 系统是 **Python 3.6.8**
- 使用 **Docker** 部署时，应用运行在**容器内部**，容器使用 **Python 3.11**
- 因此**不需要**在 ECS 上升级 Python，只要安装好 Docker 即可

---

## 二、第一步：SSH 连接 ECS

1. 打开终端（Windows 用 CMD/PowerShell，Mac 用终端）
2. 使用 SSH 连接 ECS（替换为你的 ECS 公网 IP 和用户名）：

```bash
ssh root@你的ECS公网IP
```

首次连接会提示确认指纹，输入 `yes` 回车，再输入 root 密码。

---

## 三、第二步：安装 Docker

### 3.1 检查是否已安装 Docker

```bash
docker --version
```

若显示类似 `Docker version 20.x.x`，说明已安装，可跳到第四步。

### 3.2 若未安装，执行以下命令（阿里云 ECS 常用 CentOS / AliyunLinux）

```bash
# 一键安装 Docker（使用国内镜像，加快下载）
curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun

# 启动 Docker 服务
systemctl start docker

# 设置开机自启
systemctl enable docker

# 再次检查
docker --version
```

---

## 四、第三步：安装 Git 并拉取代码

### 4.1 检查 Git 是否已安装

```bash
git --version
```

若未安装，执行：

```bash
# CentOS / AliyunLinux
yum install -y git

# Ubuntu / Debian
# apt-get update && apt-get install -y git
```

### 4.2 选择项目存放目录并克隆代码

```bash
# 进入常用目录（可改为 /home/yourname 等）
cd /opt

# 克隆 GitHub 仓库
git clone https://github.com/linyan02/InsurGuide.git

# 进入项目目录
cd InsurGuide
```

确认目录下有 `Dockerfile` 和 `requirements.txt`：

```bash
ls -la Dockerfile requirements.txt
```

---

## 五、第四步：准备 MySQL 数据库

### 5.1 登录 MySQL

```bash
mysql -u root -p
```

输入 MySQL root 密码。

### 5.2 创建数据库和用户

在 MySQL 命令行中执行（**请修改密码**）：

```sql
CREATE DATABASE insurguide CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'insurguide'@'%' IDENTIFIED BY '你设置的强密码';
GRANT ALL PRIVILEGES ON insurguide.* TO 'insurguide'@'%';
FLUSH PRIVILEGES;
EXIT;
```

说明：
- `insurguide` 为数据库名
- `insurguide` 为用户名
- `你设置的强密码` 替换为实际密码（如 `MySecure@Pass123`）

### 5.3 确认 MySQL 允许远程/本地连接

若 MySQL 仅监听 `127.0.0.1`，Docker 容器可能无法连接。可检查：

```bash
netstat -tlnp | grep 3306
```

若显示 `127.0.0.1:3306`，需让 MySQL 监听 `0.0.0.0`（编辑 `my.cnf` 中 `bind-address = 0.0.0.0` 后重启 MySQL）。  
若显示 `0.0.0.0:3306` 或 `*:3306`，则无需修改。

---

## 六、第五步：确认 Redis、ES 可访问

### 6.1 Redis

```bash
redis-cli -h 127.0.0.1 -p 6379 ping
```

应返回 `PONG`。若有密码，则：`redis-cli -h 127.0.0.1 -p 6379 -a 你的密码 ping`。

### 6.2 Elasticsearch（可选）

```bash
curl -s http://127.0.0.1:9200
```

若有返回 JSON 说明 ES 正常。

---

## 七、第六步：创建环境变量配置文件

### 7.1 复制模板并编辑

```bash
cd /opt/InsurGuide
cp .env.example .env.production
nano .env.production
```

（若无 `nano`，可用 `vi .env.production`）

### 7.2 按实际环境修改以下配置

**重点修改项**（中间件在 ECS 本机时）：

```env
# 应用
DEBUG=False
SECRET_KEY=请替换为随机字符串如MyJwtSecretKey2024Prod

# MySQL（本机部署时）
MYSQL_HOST=172.17.0.1
MYSQL_PORT=3306
MYSQL_USER=insurguide
MYSQL_PASSWORD=你在第五步设置的密码
MYSQL_DATABASE=insurguide

# Redis（本机部署时）
REDIS_HOST=172.17.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
# 若 Redis 有密码，填写：REDIS_PASSWORD=你的Redis密码

# RAGflow（必填，知识库检索）
RAGFLOW_API_URL=http://你的RAGflow地址:9380/api/v1
RAGFLOW_API_KEY=你的RAGflow-API-Key
RAGFLOW_KNOWLEDGE_BASE_ID=你的知识库ID

# 大模型（必填）
DASHSCOPE_API_KEY=你的通义千问API-Key
LLM_MODE=api

# 意图/改写（可选，默认 rule）
INTENT_MODE=rule
REWRITE_MODE=rule
```

**关于 `MYSQL_HOST` 和 `REDIS_HOST`**：
- MySQL、Redis 在 **本机** 时，Docker 容器访问宿主机常用 `172.17.0.1`
- 若 `172.17.0.1` 连不上，可用本机内网 IP：
  ```bash
  ip addr | grep inet
  ```
  取 `eth0` 或主网卡的 `inet` 地址（如 `172.16.1.100`）填入 `MYSQL_HOST`、`REDIS_HOST`

保存退出：`nano` 按 `Ctrl+O` 回车，`Ctrl+X`；`vi` 按 `Esc` 后输入 `:wq` 回车。

---

## 八、第七步：构建 Docker 镜像

```bash
cd /opt/InsurGuide
docker build -t insurguide:latest .
```

首次构建可能需 5～15 分钟（下载 Python 镜像和依赖）。若网络较慢，Dockerfile 已使用清华 pip 源，一般可正常完成。

---

## 九、第八步：运行容器

```bash
docker run -d \
  --name insurguide \
  -p 8000:8000 \
  --env-file .env.production \
  --restart unless-stopped \
  insurguide:latest
```

说明：
- `-d`：后台运行
- `--name insurguide`：容器名
- `-p 8000:8000`：宿主机 8000 端口映射到容器 8000
- `--env-file .env.production`：使用刚创建的配置
- `--restart unless-stopped`：重启后自动拉起

### 9.1 若 MySQL/Redis 用 172.17.0.1 仍然连不上

可尝试增加宿主机解析（Docker 20.10+）：

```bash
docker run -d \
  --name insurguide \
  -p 8000:8000 \
  --add-host=host.docker.internal:host-gateway \
  --env-file .env.production \
  --restart unless-stopped \
  insurguide:latest
```

并将 `.env.production` 中改为：
```env
MYSQL_HOST=host.docker.internal
REDIS_HOST=host.docker.internal
```

---

## 十、第九步：验证部署

### 10.1 查看容器状态

```bash
docker ps
```

应看到 `insurguide` 在运行。

### 10.2 查看日志（排查问题用）

```bash
docker logs -f insurguide
```

按 `Ctrl+C` 退出。

### 10.3 健康检查

```bash
curl http://localhost:8000/health
```

期望返回：`{"status":"healthy"}`

### 10.4 浏览器访问

- API 文档：`http://你的ECS公网IP:8000/docs`
- Web 页面：`http://你的ECS公网IP:8000/static/index.html`

若无法访问，需在**阿里云安全组**中放通 **8000** 端口（见下一步）。

---

## 十一、第十步：配置阿里云安全组

1. 登录 [阿里云控制台](https://ecs.console.aliyun.com/)
2. 进入 **ECS → 实例**，找到对应实例
3. 点击 **安全组** → **配置规则** → **入方向** → **手动添加**
4. 规则示例：
   - 端口范围：`8000/8000`
   - 授权对象：`0.0.0.0/0`（仅测试用）或指定 IP
   - 协议：TCP
5. 保存

配置后即可通过公网 IP 访问 `http://ECS公网IP:8000/docs`。

---

## 十二、后续：一键更新部署

代码有更新时，在 ECS 上执行：

```bash
cd /opt/InsurGuide
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

脚本会：`git pull` → 重新构建镜像 → 停止旧容器 → 启动新容器。

### 十二点一、为什么每次构建都这么慢？如何加速？

**原因说明**：

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 首次构建 | 5～15 分钟 | 需下载 Python 基础镜像、执行 apt-get、安装大量 Python 依赖（如 chromadb、faiss、sentence-transformers 等），耗时主要集中在 `pip install` |
| 仅代码更新后的构建 | 约 30 秒～2 分钟 | Docker 会利用**层缓存**：若 `requirements.txt` 未变，`pip install` 步骤会被跳过，只重新复制代码并生成新镜像 |

**若每次更新都感觉像“全量重建”很慢**，常见原因：

1. **`requirements.txt` 经常变动**：一旦改动，会重新执行 `pip install`，耗时明显
2. **执行过 `docker system prune`**：会清理构建缓存，下次构建需重新下载和安装
3. **在全新环境或新机器上部署**：没有历史缓存，必然是全量构建

**加速建议**（满足“拉取最新代码后，用最新代码部署”的需求）：

- **保持默认构建**：`deploy.sh` 已使用 `docker build`（未加 `--no-cache`），Docker 会自动利用缓存
- **只改业务代码时**：构建应较快（约 1 分钟内），因为依赖层被缓存
- **依赖变更时**：`requirements.txt` 改动后的第一次构建会较慢，属正常现象

若想进一步加速首次或依赖变更后的构建，可启用 BuildKit 缓存（需 Docker 20.10+）：

```bash
# 设置环境变量启用 BuildKit（一次性，或加入 ~/.bashrc）
export DOCKER_BUILDKIT=1

# 之后照常执行部署
./scripts/deploy.sh
```

启用后，pip 下载的包会被缓存，后续构建可明显缩短。

---

## 十二点五、配置命令别名（在任何目录都能执行部署）

配置完成后，在任意目录输入 `insurguide-deploy` 即可自动完成拉代码和部署，无需先 `cd` 到项目目录。

### 步骤 1：SSH 连接 ECS

用终端连接服务器（与前面相同）：

```bash
ssh root@你的ECS公网IP
```

### 步骤 2：确认项目路径

先确认 InsurGuide 项目在哪个目录（常见是 `/opt/InsurGuide`）：

```bash
ls -la /opt/InsurGuide
```

如果显示目录内容（如 Dockerfile、scripts 等），说明路径正确。  
若项目在其他位置，如 `/home/ubuntu/InsurGuide`，后面把 `/opt/InsurGuide` 改成你的实际路径。

### 步骤 3：把别名写入配置文件

复制下面整行（包括引号）并执行：

```bash
echo 'alias insurguide-deploy="cd /opt/InsurGuide && ./scripts/deploy.sh"' >> ~/.bashrc
```

说明：
- `echo`：输出一段文字
- `>>`：追加到文件末尾（不覆盖）
- `~/.bashrc`：每次登录或打开新终端时会自动执行
- 若项目不在 `/opt/InsurGuide`，把路径改成你的实际路径，例如：`/home/ubuntu/InsurGuide`

### 步骤 4：让配置立刻生效

```bash
source ~/.bashrc
```

执行后，当前终端里的别名已生效。

### 步骤 5：验证别名是否生效

输入：

```bash
insurguide-deploy
```

若开始执行拉代码、构建等流程，说明配置成功。

### 步骤 6：以后如何使用

以后每次部署时：

1. SSH 连接 ECS
2. 在任意目录输入 `insurguide-deploy` 回车
3. 等待脚本执行完成即可

### 可选：再添加几个常用别名

```bash
# 查看 InsurGuide 容器日志
echo 'alias insurguide-logs="docker logs -f insurguide"' >> ~/.bashrc

# 健康检查
echo 'alias insurguide-health="curl -s http://localhost:8000/health"' >> ~/.bashrc

source ~/.bashrc
```

之后可以用：
- `insurguide-logs`：查看实时日志（Ctrl+C 退出）
- `insurguide-health`：检查服务是否正常

### 如何查看已添加的别名

```bash
grep insurguide ~/.bashrc
```

会列出所有与 insurguide 相关的别名。

---

## 十三、常见问题排查

| 现象 | 处理 |
|------|------|
| `docker: command not found` | 按第三步重新安装 Docker |
| `git: command not found` | 执行 `yum install -y git` 或 `apt install -y git` |
| 容器启动后马上退出 | `docker logs insurguide` 查报错；常见为 MySQL/Redis 连不上 |
| 健康检查 200，但对话 500 | 查看 `docker logs insurguide`，检查 DASHSCOPE_API_KEY、RAGflow 配置 |
| 外网无法访问 | 检查安全组是否放通 8000，防火墙是否开放 8000 |
| MySQL 连接失败 | 确认 `MYSQL_HOST` 用 `172.17.0.1` 或 `host.docker.internal`，MySQL 监听 `0.0.0.0` |
| Redis 连接失败 | 同上，检查 `REDIS_HOST` 和 Redis 监听地址 |

---

## 十四、一键部署命令汇总（复制执行）

假设你已完成：MySQL 建库、创建 `.env.production`、RAGflow 与通义 Key 已就绪。

```bash
cd /opt
git clone https://github.com/linyan02/InsurGuide.git
cd InsurGuide

# 编辑配置（务必修改 MySQL、Redis、RAGflow、DASHSCOPE_API_KEY 等）
cp .env.example .env.production
nano .env.production

# 构建并运行
docker build -t insurguide:latest .
docker run -d --name insurguide -p 8000:8000 --env-file .env.production --restart unless-stopped insurguide:latest

# 验证
curl http://localhost:8000/health
```

---

## 十五、RAGflow 说明

RAGflow 是知识库检索服务，需单独部署。若尚未部署：

1. 参考 [RAGflow 官方文档](https://github.com/infiniflow/ragflow) 部署
2. 或使用已有 RAGflow 服务地址，将 `RAGFLOW_API_URL`、`RAGFLOW_API_KEY`、`RAGFLOW_KNOWLEDGE_BASE_ID` 填入 `.env.production`

在 RAGflow 中创建知识库并上传保险相关文档后，将知识库 ID 填入 `RAGFLOW_KNOWLEDGE_BASE_ID`。

---

**文档版本**：v1.0  
**项目地址**：<https://github.com/linyan02/InsurGuide.git>
