"""
向量数据库页：相似度检索

需先登录获取 Token，API 地址从 config 统一读取。
"""
import requests
import gradio as gr

from gradio_ui.config import API_VECTOR_QUERY


def _query(query_text: str, n_results: int, token: str) -> str:
    if not (token or "").strip():
        return "请先登录获取 Token"
    try:
        r = requests.post(
            API_VECTOR_QUERY(),
            json={"query_texts": [query_text], "n_results": n_results},
            headers={"Authorization": f"Bearer {token.strip()}"},
            timeout=15,
        )
        if r.status_code == 200:
            return f"查询结果: {r.json().get('results', {})}"
        return f"查询失败: {r.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"查询错误: {str(e)}"


def render():
    """渲染「向量数据库」Tab。"""
    with gr.Tab("🔍 向量数据库"):
        gr.Markdown("### 查询向量数据库")
        vector_token = gr.Textbox(label="Token", placeholder="请输入登录后获取的 Token")
        vector_query = gr.Textbox(label="查询文本", placeholder="请输入要查询的内容")
        vector_n_results = gr.Slider(minimum=1, maximum=20, value=5, label="返回结果数量")
        vector_btn = gr.Button("查询", variant="primary")
        vector_output = gr.Textbox(label="查询结果", lines=10)
        vector_btn.click(
            fn=_query,
            inputs=[vector_query, vector_n_results, vector_token],
            outputs=vector_output,
        )
