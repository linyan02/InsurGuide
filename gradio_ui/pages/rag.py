"""
增强 RAG 对话页（智保灵犀）：多轮对话、溯源、意图与改写

调用统一配置中的 /api/chat，不硬编码 URL。
"""
import requests
import gradio as gr

from gradio_ui.config import API_CHAT


def _chat(user_id: str, query: str) -> tuple:
    user_id = (user_id or "").strip()
    query = (query or "").strip()
    if not user_id:
        return "请输入用户 ID（唯一标识）", ""
    if not query:
        return "请输入提问内容", ""
    try:
        r = requests.post(
            API_CHAT(),
            json={"user_id": user_id, "query": query},
            timeout=30,
        )
        data = r.json()
        if data.get("code") != 200:
            return data.get("message", "请求失败"), ""
        d = data.get("data") or {}
        answer = d.get("answer", "")
        sources = d.get("source") or []
        count = d.get("context_count", 0)
        violated = d.get("violated", False)
        intent_cn = d.get("intent_cn", "")
        rewritten = d.get("rewritten_query", "")
        rewrite_changed = d.get("rewrite_changed", False)
        source_text = "来源：" + "、".join(sources) if sources else "无"
        if violated:
            source_text += "（已做合规屏蔽）"
        lines = [f"当前对话轮数：{count}", f"意图识别：{intent_cn}", source_text]
        if rewrite_changed and rewritten:
            lines.append(f"检索用改写问题：{rewritten}")
        return answer, "\n".join(lines)
    except Exception as e:
        return f"请求错误: {str(e)}", ""


def render():
    """渲染「增强 RAG 对话」Tab。"""
    with gr.Tab("🦉 增强 RAG 对话"):
        gr.Markdown("### 智保灵犀 - 多轮对话（RAGflow 知识库 + 合规校验）")
        rag_user_id = gr.Textbox(label="用户 ID", placeholder="用于多轮上下文的唯一标识")
        rag_query = gr.Textbox(label="提问", placeholder="例如：重疾险甲状腺结节核保规则")
        rag_btn = gr.Button("发送", variant="primary")
        rag_answer = gr.Textbox(label="答案", lines=8)
        rag_meta = gr.Textbox(label="溯源与轮数", lines=3)
        rag_btn.click(
            fn=_chat,
            inputs=[rag_user_id, rag_query],
            outputs=[rag_answer, rag_meta],
        )
