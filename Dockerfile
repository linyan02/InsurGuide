# InsurGuide 智保灵犀 - API 服务镜像（供阿里云 ECS 等部署）
# 中间件（MySQL/Redis/RAGflow）已在宿主机或其它容器，本镜像仅运行 FastAPI 应用

FROM python:3.11-slim

WORKDIR /app

# 系统依赖（ChromaDB/向量等可能用到）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 依赖先复制并安装，便于利用镜像缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 应用代码
COPY config/ ./config/
COPY core/ ./core/
COPY services/ ./services/
COPY api/ ./api/
COPY routers/ ./routers/
COPY app/ ./app/
COPY models/ ./models/
COPY utils/ ./utils/
COPY web/ ./web/
COPY config.py .
COPY main.py .

# 兼容：部分代码可能 from config import settings，需能解析 config 包
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 生产环境关闭调试（pydantic-settings 会读取环境变量）
ENV DEBUG=false

EXPOSE 8000

# 多 worker 提升并发（可按 CPU 核数调整 --workers）
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
