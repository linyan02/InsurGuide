"""
用户认证页：登录、注册

所有 API 地址与路由从 gradio_ui.config 统一读取，不硬编码。
"""
import requests
import gradio as gr

from gradio_ui.config import API_AUTH_LOGIN, API_AUTH_REGISTER


def _login(username: str, password: str) -> str:
    try:
        r = requests.post(
            API_AUTH_LOGIN(),
            data={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            token = r.json().get("access_token", "")
            if token:
                return f"登录成功！请复制下方 Token 到「对话服务」Tab 的 Token 输入框以使用条款功能：\n\n{token}"
            return "登录成功，但未返回 Token"
        return f"登录失败: {r.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"登录错误: {str(e)}"


def _register(username: str, email: str, password: str) -> str:
    try:
        r = requests.post(
            API_AUTH_REGISTER(),
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        if r.status_code == 201:
            return "注册成功！"
        return f"注册失败: {r.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"注册错误: {str(e)}"


def render():
    """在当前 Blocks 的 Tabs 下渲染「用户认证」Tab。"""
    with gr.Tab("🔐 用户认证"):
        with gr.Row():
            with gr.Column():
                gr.Markdown("### 登录")
                login_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                login_password = gr.Textbox(label="密码", type="password", placeholder="请输入密码")
                login_btn = gr.Button("登录", variant="primary")
                login_output = gr.Textbox(label="登录结果", lines=3)
                login_btn.click(
                    fn=_login,
                    inputs=[login_username, login_password],
                    outputs=login_output,
                )
            with gr.Column():
                gr.Markdown("### 注册")
                reg_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                reg_email = gr.Textbox(label="邮箱", placeholder="请输入邮箱")
                reg_password = gr.Textbox(label="密码", type="password", placeholder="请输入密码")
                reg_btn = gr.Button("注册", variant="primary")
                reg_output = gr.Textbox(label="注册结果", lines=3)
                reg_btn.click(
                    fn=_register,
                    inputs=[reg_username, reg_email, reg_password],
                    outputs=reg_output,
                )
