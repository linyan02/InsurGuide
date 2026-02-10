"""
页头组件：Logo + 应用标题与副标题

Logo 优先使用配置 GRADIO_LOGO_PATH，否则使用包内 logo_placeholder.png，
为首页预留统一品牌区域，后续替换为真实 Logo 即可。
"""
import gradio as gr

from gradio_ui.config import get_app_name, get_logo_path


def render_header():
    """在当前 Blocks 中渲染页头：一行左侧 Logo（占位或配置图）、右侧标题与副标题。"""
    logo_path = get_logo_path()
    app_name = get_app_name()

    with gr.Row(elem_id="app_header", variant="default"):
        # Logo 区域：有路径则显示图片，无则显示占位块，保证首页始终预留 Logo 位置
        if logo_path:
            gr.Image(
                value=logo_path,
                show_label=False,
                show_download_button=False,
                container=False,
                height=50,
                elem_id="app_logo",
            )
        else:
            gr.HTML(
                '<div style="width:120px;height:50px;background:#f0f0f0;border:1px solid #e0e0e0;'
                'display:flex;align-items:center;justify-content:center;color:#999;font-size:12px;">Logo</div>',
                elem_id="app_logo",
            )
        with gr.Column(scale=10, min_width=200):
            gr.Markdown(f"# 🛡️ {app_name} - 智能保险指南系统", elem_id="app_title")
            gr.Markdown("基于 FastAPI、LangChain 和 Gradio 构建的智能保险指南平台", elem_id="app_subtitle")
