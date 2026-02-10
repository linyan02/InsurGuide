# 核心基础设施：认证（兼容旧导入，routers/auth 等可能 from app.auth 引用）
from core.auth import (
    create_access_token,
    get_current_active_user,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
    authenticate_user,
    verify_password,
    oauth2_scheme,
)

__all__ = [
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "get_user_by_username",
    "get_user_by_email",
    "authenticate_user",
    "get_current_user",
    "get_current_active_user",
    "oauth2_scheme",
]
