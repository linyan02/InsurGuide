"""
InsurGuide 主应用
FastAPI 主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from routers import auth, vector, es
from config import settings

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="InsurGuide - 基于 FastAPI、LangChain 和 Gradio 的智能保险指南系统"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(vector.router)
app.include_router(es.router)


@app.get("/")
def root():
    """根路径"""
    return {
        "message": f"欢迎使用 {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
