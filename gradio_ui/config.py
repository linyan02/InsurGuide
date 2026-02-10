"""
Gradio 前端统一配置

从项目 config 读取 API 基地址、路由路径、Logo 等，前端模块仅依赖本模块与 config，
不硬编码 URL 与路径，便于环境切换与维护。
"""
import os

from config import settings
from config.constants import (
    GRADIO_ROUTE_AUTH_LOGIN,
    GRADIO_ROUTE_AUTH_REGISTER,
    GRADIO_ROUTE_CHAT,
    GRADIO_ROUTE_CHAT_CLEAR,
    GRADIO_ROUTE_ES_SEARCH,
    GRADIO_ROUTE_VECTOR_QUERY,
)


def get_api_base_url() -> str:
    """后端 API 根地址，末尾无斜杠。"""
    url = (getattr(settings, "GRADIO_API_BASE_URL", None) or "http://localhost:8000").strip()
    return url.rstrip("/")


def get_full_url(path: str) -> str:
    """拼接完整请求 URL。"""
    return f"{get_api_base_url()}{path}"


# 供各页面直接使用的完整 API 地址
API_AUTH_LOGIN = lambda: get_full_url(GRADIO_ROUTE_AUTH_LOGIN)
API_AUTH_REGISTER = lambda: get_full_url(GRADIO_ROUTE_AUTH_REGISTER)
API_CHAT = lambda: get_full_url(GRADIO_ROUTE_CHAT)
API_CHAT_CLEAR = lambda: get_full_url(GRADIO_ROUTE_CHAT_CLEAR)
API_VECTOR_QUERY = lambda: get_full_url(GRADIO_ROUTE_VECTOR_QUERY)
API_ES_SEARCH = lambda: get_full_url(GRADIO_ROUTE_ES_SEARCH)


def get_logo_path() -> str:
    """
    首页 Logo 图片路径。若配置 GRADIO_LOGO_PATH 且文件存在则使用，否则使用包内占位图。
    """
    custom = (getattr(settings, "GRADIO_LOGO_PATH", None) or "").strip()
    if custom and os.path.isfile(custom):
        return os.path.abspath(custom)
    default = os.path.join(os.path.dirname(__file__), "static", "logo_placeholder.png")
    if os.path.isfile(default):
        return default
    return ""


def get_app_name() -> str:
    """应用名称，用于标题与页头。"""
    return getattr(settings, "APP_NAME", "InsurGuide")


def get_gradio_launch_config() -> dict:
    """Gradio launch 参数：server_name, server_port, share。"""
    return {
        "server_name": "0.0.0.0",
        "server_port": getattr(settings, "GRADIO_PORT", 7860),
        "share": getattr(settings, "GRADIO_SHARE", False),
    }
