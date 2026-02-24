#!/usr/bin/env bash
# InsurGuide 一键部署脚本（阿里云 ECS Docker）
# 用法：在项目根目录执行 ./scripts/deploy.sh，或 cd 到项目根后 bash scripts/deploy.sh
# 首次部署前请先完成：git clone、创建 .env.production、首次 docker build 与 run

set -e

# 项目根目录（脚本所在目录的上一级）
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

IMAGE_NAME="${IMAGE_NAME:-insurguide:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-insurguide}"
ENV_FILE="${ENV_FILE:-.env.production}"
PORT="${PORT:-8000}"

echo "[InsurGuide] 项目目录: $ROOT_DIR"
echo "[InsurGuide] 镜像: $IMAGE_NAME  容器: $CONTAINER_NAME  端口: $PORT"
echo ""

# 1. 拉取最新代码
echo "[1/4] 拉取最新代码..."
git pull

# 2. 构建镜像
echo "[2/4] 构建 Docker 镜像..."
docker build -t "$IMAGE_NAME" .

# 3. 停止并删除旧容器（存在则执行）
echo "[3/4] 停止并移除旧容器..."
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  docker stop "$CONTAINER_NAME" 2>/dev/null || true
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
else
  echo "         (无已存在容器，跳过)"
fi

# 4. 启动新容器
if [ ! -f "$ENV_FILE" ]; then
  echo "[错误] 未找到环境变量文件: $ENV_FILE"
  echo "请先创建 $ENV_FILE（可参考 .env.example），填写 MySQL、Redis、RAGflow 等配置。"
  exit 1
fi

echo "[4/4] 启动新容器..."
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:8000" \
  --env-file "$ENV_FILE" \
  --restart unless-stopped \
  "$IMAGE_NAME"

echo ""
echo "[InsurGuide] 部署完成。"
echo "  查看日志: docker logs -f $CONTAINER_NAME"
echo "  健康检查: curl http://localhost:$PORT/health"
echo ""
