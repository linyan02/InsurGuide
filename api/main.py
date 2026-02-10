"""
API 服务入口：FastAPI 应用创建与路由注册

本模块创建 FastAPI 实例、挂载 CORS、注册所有路由（认证、对话、向量库、ES、意图/改写规则），
并根据表结构自动创建 MySQL 表。供 PC Web、小程序等前端通过同一套 API 调用。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from config import settings
from core.database import Base, engine, get_db
from routers import auth, vector, es, chat, intent_rewrite_rules
import models.chat_log  # 引入以注册 ORM 表，便于 create_all 建表

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="InsurGuide - 智保灵犀增强 RAG 系统，API 供 Web/小程序使用",
)

# 允许前端跨域访问（开发时可设具体域名，生产建议收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(vector.router)
app.include_router(es.router)
app.include_router(chat.router)
app.include_router(intent_rewrite_rules.router)

# 若存在 web/static 目录，则挂载为 /static，前端可访问 /static/index.html
web_static = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "static")
if os.path.isdir(web_static):
    app.mount("/static", StaticFiles(directory=web_static), name="static")


@app.get("/")
def root():
    """根路径：返回欢迎信息与文档/静态页链接。"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "web": "/static/index.html" if os.path.isdir(web_static) else None,
    }


@app.get("/health")
def health_check():
    """健康检查：供负载均衡或运维探测。"""
    return {"status": "healthy"}
