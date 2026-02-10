"""
Gradio 演示应用入口

前端采用模块化架构：配置与路由统一从 config 读取，各页面在 gradio_ui.pages 中独立实现。
运行方式：python gradio_app.py（需先启动后端 API：python main.py）
"""
from gradio_ui.app import launch_demo

if __name__ == "__main__":
    launch_demo()
