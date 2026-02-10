"""
Elasticsearch 页：索引搜索

需先登录，API 地址从 config 统一读取。
"""
import requests
import gradio as gr

from gradio_ui.config import API_ES_SEARCH


def _search(index: str, query_text: str, token: str) -> str:
    if not (token or "").strip():
        return "请先登录获取 Token"
    try:
        r = requests.post(
            API_ES_SEARCH(),
            json={
                "index": index or "insurguide",
                "query": {"match": {"_all": query_text}},
            },
            headers={"Authorization": f"Bearer {token.strip()}"},
            timeout=15,
        )
        if r.status_code == 200:
            return f"搜索结果: {r.json().get('results', {})}"
        return f"搜索失败: {r.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"搜索错误: {str(e)}"


def render():
    """渲染「Elasticsearch」Tab。"""
    with gr.Tab("📊 Elasticsearch"):
        gr.Markdown("### 搜索 Elasticsearch")
        es_token = gr.Textbox(label="Token", placeholder="请输入登录后获取的 Token")
        es_index = gr.Textbox(label="索引名称", placeholder="请输入索引名称", value="insurguide")
        es_query = gr.Textbox(label="搜索文本", placeholder="请输入要搜索的内容")
        es_btn = gr.Button("搜索", variant="primary")
        es_output = gr.Textbox(label="搜索结果", lines=10)
        es_btn.click(
            fn=_search,
            inputs=[es_index, es_query, es_token],
            outputs=es_output,
        )
