# 核心基础设施：ES 客户端（兼容旧导入，routers/es 等可能 from app.es_client 引用）
from core.es_client import ESClient, get_es_client

__all__ = ["ESClient", "get_es_client"]
