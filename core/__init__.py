"""
核心基础设施层：数据库、Redis、向量库、ES

本包提供全项目共用的底层能力：
- database：MySQL 连接与会话，get_db 供 FastAPI 依赖注入
- redis_store：多轮对话上下文的存取与清理
- vector_db：ChromaDB 单例，存意图/改写规则
- es_client：Elasticsearch 客户端（可选）
认证相关在 core.auth，由 API 层直接依赖。
"""
from core.database import Base, engine, get_db, SessionLocal
from core.redis_store import (
    get_conversation_context,
    save_conversation_context,
    clear_conversation_context,
)
from core.vector_db import vector_db
from core.es_client import get_es_client

__all__ = [
    "Base",
    "engine",
    "get_db",
    "SessionLocal",
    "get_conversation_context",
    "save_conversation_context",
    "clear_conversation_context",
    "vector_db",
    "get_es_client",
]
