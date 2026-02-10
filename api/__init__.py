"""
API 接口服务层：供 PC Web 与小程序复用

通过 from api import app 拿到 FastAPI 应用，由 main.py 或 uvicorn 启动。
"""
from api.main import app

__all__ = ["app"]
