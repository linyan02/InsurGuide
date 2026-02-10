"""
Gradio 前端 UI 包

采用模块化架构：配置与路由统一从 config 读取，各页面独立实现，
便于后续优化升级且互不影响。入口为 app.build_demo()。
"""
from gradio_ui.app import build_demo

__all__ = ["build_demo"]
