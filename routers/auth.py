"""
认证路由 - 注册、登录、获取当前用户

- POST /api/auth/register：注册新用户（用户名、邮箱、密码）
- POST /api/auth/login：登录，返回 JWT access_token，后续请求需在 Header 带 Authorization: Bearer <token>
- GET /api/auth/me：获取当前登录用户信息（需已登录）
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from core.database import get_db
from core.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_user_by_username,
    get_user_by_email,
    get_current_active_user
)
from models.user import User
from config import settings

router = APIRouter(prefix="/api/auth", tags=["认证"])


class UserCreate(BaseModel):
    """注册请求体：用户名、邮箱、密码。"""
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """返回给前端的用户信息（不含密码）。"""
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    """登录成功后的响应：access_token 用于后续接口鉴权。"""
    access_token: str
    token_type: str


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册：校验用户名、邮箱不重复后，密码哈希入库。"""
    # 检查用户名是否已存在
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    
    # 检查邮箱是否已存在
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已存在"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """用户登录：校验用户名密码，通过则签发 JWT 返回。"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前登录用户信息，需在 Header 带有效 Bearer token。"""
    return current_user
