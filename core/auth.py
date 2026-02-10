"""
JWT 认证 - 供 API 层依赖

登录流程：用户提交用户名+密码 → 校验通过后用 SECRET_KEY 签发一个 JWT token →
前端之后每次请求在 Header 里带 Authorization: Bearer <token> →
本模块的 get_current_user 会解析 token 并查出对应用户，供需要「已登录」的接口使用。
密码在数据库里存的是 bcrypt 哈希，不会存明文。
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import settings
from core.database import get_db
from models.user import User

# 密码加密用 bcrypt，安全性好
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# 声明「密码模式」的 OAuth2：token 从 api/auth/login 这个地址拿
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码和数据库里的哈希是否一致。"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """注册时把用户输入的密码转成哈希再存库，不能存明文。"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    签发 JWT。data 里通常有 sub=用户名，exp 是过期时间。
    前端拿到的就是这个 token，后续请求都要带上。
    """
    to_encode = data.copy()
    expire = (
        datetime.utcnow() + expires_delta
        if expires_delta
        else datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """按用户名查用户，没有则返回 None。"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """按邮箱查用户，注册时用来判断邮箱是否已被占用。"""
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """登录时用：用户名+密码都对了才返回用户对象，否则返回 None。"""
    user = get_user_by_username(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI 依赖：从请求头里取出 Bearer token，解析出用户名，再查库得到用户对象。
    解析失败或用户不存在会抛 401，接口里用 Depends(get_current_user) 即可要求「已登录」。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_username(db, username=username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """在「已登录」基础上再要求用户未被禁用（is_active=True）。"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user
