"""
对话服务页：二选一 —— 自建增强 RAG（智保灵犀）或 直接对话大模型

通过单选切换模式，两种能力互不干扰，共用同一 Tab。
"""
import os
import requests
import gradio as gr

from gradio_ui.config import API_CHAT

# 延迟初始化 LLM，仅在选择「直接对话大模型」时使用
_llm = None


def _get_llm():
    global _llm
    if _llm is not None:
        return _llm
    try:
        from langchain_openai import ChatOpenAI
        if os.getenv("OPENAI_API_KEY"):
            _llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")
            return _llm
    except ImportError:
        try:
            from langchain.llms import OpenAI
            if os.getenv("OPENAI_API_KEY"):
                _llm = OpenAI(temperature=0.7)
                return _llm
        except ImportError:
            pass
    except Exception:
        pass
    return None


def _chat_rag(user_id: str, query: str) -> tuple:
    """自建增强 RAG：调用 /api/chat。"""
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


def _chat_llm(message: str, history: list) -> tuple:
    """直接对话大模型：LangChain 直连 LLM。"""
    llm = _get_llm()
    if llm is None:
        return "", history + [(message, "请设置 OPENAI_API_KEY 环境变量后再使用直接对话大模型。")]
    try:
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        prompt = PromptTemplate(
            input_variables=["question"],
            template="你是一个专业的保险顾问。请回答以下问题：{question}",
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        reply = chain.run(message)
        return "", history + [(message, reply or "")]
    except Exception as e:
        return "", history + [(message, f"LLM 错误: {str(e)}")]


def _toggle_mode(choice: str) -> tuple:
    """根据选择显示/隐藏对应区域。"""
    is_rag = choice == "自建增强 RAG"
    return (
        gr.update(visible=is_rag),
        gr.update(visible=not is_rag),
    )


def render():
    """渲染「对话服务」Tab：模式选择 + 增强 RAG 区域 + 直接对话大模型区域。"""
    with gr.Tab("💬 对话服务"):
        gr.Markdown("### 选择对话方式")
        mode = gr.Radio(
            choices=["自建增强 RAG", "直接对话大模型"],
            value="自建增强 RAG",
            label="对话模式",
        )

        # 自建增强 RAG 区域
        with gr.Column(visible=True) as col_rag:
            gr.Markdown("**智保灵犀**：基于 RAGflow 知识库的多轮对话，含意图识别、问题改写与合规校验。")
            rag_user_id = gr.Textbox(label="用户 ID", placeholder="用于多轮上下文的唯一标识")
            rag_query = gr.Textbox(label="提问", placeholder="例如：重疾险甲状腺结节核保规则")
            rag_btn = gr.Button("发送", variant="primary")
            rag_answer = gr.Textbox(label="答案", lines=8)
            rag_meta = gr.Textbox(label="溯源与轮数", lines=3)
            rag_btn.click(
                fn=_chat_rag,
                inputs=[rag_user_id, rag_query],
                outputs=[rag_answer, rag_meta],
            )

        # 直接对话大模型区域
        with gr.Column(visible=False) as col_llm:
            gr.Markdown("**直接对话大模型**：不经过知识库检索，由大模型直接回答（需配置 OPENAI_API_KEY）。")
            llm_chatbot = gr.Chatbot(label="对话历史")
            llm_msg = gr.Textbox(label="输入消息", placeholder="请输入您的问题...")
            llm_clear = gr.Button("清空对话")
            llm_msg.submit(_chat_llm, [llm_msg, llm_chatbot], [llm_msg, llm_chatbot])
            llm_clear.click(lambda: None, None, llm_chatbot, queue=False)

        mode.change(
            fn=_toggle_mode,
            inputs=[mode],
            outputs=[col_rag, col_llm],
        )
