"""
用户数据模型 - 对应 MySQL 表 users

用于注册、登录、JWT 鉴权。密码存 hashed_password（bcrypt），不存明文。
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from core.database import Base


class User(Base):
    """
    用户表 ORM 模型。注册时写入 username、email、hashed_password；
    登录成功后用 username 作为 JWT 的 sub。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)  # bcrypt 哈希，不可逆
    is_active = Column(Boolean, default=True)   # 禁用用户时改为 False
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
