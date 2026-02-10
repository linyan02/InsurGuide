"""
Gradio 应用主入口：组装页头与各功能 Tab，统一配置驱动

仅保留：注册、登录、对话服务（自建增强 RAG / 直接对话大模型 二选一）。
"""
import gradio as gr

from gradio_ui.config import get_app_name, get_gradio_launch_config
from gradio_ui.components import render_header
from gradio_ui.pages import render_auth, render_chat


def build_demo() -> gr.Blocks:
    """
    构建 Gradio 应用：首页 Logo + 标题，下方为 Tab（用户认证、对话服务）。
    对话服务内可选择：自建增强 RAG 或 直接对话大模型。
    """
    title = f"{get_app_name()} - 智能保险指南系统"
    with gr.Blocks(title=title, css="""
        #app_header { margin-bottom: 0.5rem; }
        #app_logo img { object-fit: contain; }
    """) as demo:
        render_header()
        with gr.Tabs():
            render_auth()
            render_chat()
    return demo


def launch_demo():
    """构建并启动 Gradio 服务。"""
    demo = build_demo()
    kwargs = get_gradio_launch_config()
    demo.launch(**kwargs)
