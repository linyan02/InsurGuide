"""
InsurGuide 统一入口 - 智保灵犀增强 RAG 系统

直接运行本文件即启动 FastAPI 服务（默认 0.0.0.0:8000），供 PC Web、小程序等调用。
DEBUG=True 时会开启热重载。Gradio 演示页需单独运行：python gradio_app.py
"""
from api.main import app

if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
