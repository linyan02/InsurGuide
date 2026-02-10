# 核心基础设施：向量库（兼容旧导入，app/intent、app/query_rewrite 等可能写 from app.vector_db import vector_db）
from core.vector_db import vector_db, VectorDB

__all__ = ["vector_db", "VectorDB"]
