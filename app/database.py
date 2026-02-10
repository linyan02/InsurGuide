# 核心基础设施：数据库（兼容旧导入，避免改动大量 from app.database 的引用）
from core.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
