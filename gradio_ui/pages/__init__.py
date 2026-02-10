"""
各功能页（Tab）模块：认证、对话服务

对话服务内可选「自建增强 RAG」或「直接对话大模型」。向量库、ES 等已从主界面移除，模块文件仍保留便于复用。
"""
from gradio_ui.pages.auth import render as render_auth
from gradio_ui.pages.chat import render as render_chat

__all__ = [
    "render_auth",
    "render_chat",
]
