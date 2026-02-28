"""
对话服务页：二选一 —— 自建增强 RAG（智保灵犀）或 直接对话大模型

P2-10：智保灵犀区域增加「上传条款」、条款状态、清除，与 PC Web 一致。
"""
import os
import time
import os.path as osp
import random
import string
import requests
import gradio as gr

from gradio_ui.config import (
    API_CHAT,
    API_CLAUSE_UPLOAD,
    API_CLAUSE_CLEAR,
)


def _gen_session_id() -> str:
    return f"sess_{int(time.time())}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


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


def _upload_clause(file, token: str, session_id: str) -> tuple:
    """上传条款文件。返回 (status_msg, new_session_id, file_name)"""
    if file is None:
        return "请选择文件", session_id, ""
    if isinstance(file, list) and file:
        file = file[0]
    path = getattr(file, "name", None) or (file if isinstance(file, str) else None)
    orig_name = getattr(file, "orig_name", None) or (osp.basename(path) if path else "upload.pdf")
    if not path or not isinstance(path, str):
        return "无效文件", session_id, ""
    token = (token or "").strip()
    if not token:
        return "条款上传需先登录，请填写 Token", session_id, ""
    sid = session_id or _gen_session_id()
    try:
        with open(path, "rb") as f:
            files = {"file": (orig_name, f)}
            headers = {"Authorization": f"Bearer {token}"}
            r = requests.post(
                API_CLAUSE_UPLOAD(),
                params={"session_id": sid},
                files=files,
                headers=headers,
                timeout=60,
            )
        if r.status_code != 200:
            err = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            msg = err.get("detail", r.text or "上传失败")
            if isinstance(msg, list) and msg and isinstance(msg[0], dict):
                msg = msg[0].get("msg", str(msg))
            return f"上传失败: {msg}", sid, ""
        data = r.json()
        fn = data.get("file_name", orig_name or "条款")
        return f"已加载：{fn}", sid, fn
    except Exception as e:
        return f"请求错误: {str(e)}", sid, ""


def _clear_clause(token: str, session_id: str) -> tuple:
    """清除条款上下文。返回 (msg, session_id)"""
    token = (token or "").strip()
    if not token:
        return "请先填写 Token", session_id
    sid = session_id or "default"
    try:
        r = requests.post(
            API_CLAUSE_CLEAR(),
            json={"session_id": sid},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if r.status_code != 200:
            return "清除失败", sid
        return "已清除条款", sid
    except Exception as e:
        return f"请求错误: {str(e)}", sid


def _chat_rag(user_id: str, query: str, token: str, session_id: str) -> tuple:
    """自建增强 RAG：调用 /api/chat，带 session_id 以绑定条款上下文。"""
    user_id = (user_id or "").strip()
    query = (query or "").strip()
    if not user_id:
        return "请输入用户 ID（唯一标识，条款功能请填登录名）", ""
    if not query:
        return "请输入提问内容", ""
    sid = session_id or "default"
    try:
        body = {"user_id": user_id, "query": query, "session_id": sid}
        headers = {"Content-Type": "application/json"}
        if (token or "").strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        r = requests.post(
            API_CHAT(),
            json=body,
            headers=headers,
            timeout=60,
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
        clause_loaded = d.get("clause_loaded", False)
        source_text = "来源：" + "、".join(sources) if sources else "无"
        if violated:
            source_text += "（已做合规屏蔽）"
        lines = [f"当前对话轮数：{count}", f"意图识别：{intent_cn}", source_text]
        if clause_loaded:
            lines.append("📄 基于您上传的条款")
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

        with gr.Column(visible=True) as col_rag:
            gr.Markdown("**智保灵犀**：基于 RAGflow 知识库的多轮对话，含意图识别、问题改写与合规校验。")
            rag_token = gr.Textbox(
                label="Token（条款功能需登录后填写）",
                type="password",
                placeholder="在认证 Tab 登录后，从返回结果复制 token 到此",
            )
            rag_user_id = gr.Textbox(
                label="用户 ID",
                placeholder="用于多轮上下文；条款功能请填与登录名一致",
            )
            rag_session_id = gr.State(value="")

            with gr.Row():
                rag_file = gr.File(label="上传条款", file_types=[".pdf", ".doc", ".docx", ".txt"])
                rag_upload_btn = gr.Button("📎 上传条款", variant="secondary")
            rag_clause_status = gr.Textbox(
                label="条款状态",
                value="",
                interactive=False,
                visible=True,
            )
            rag_clear_btn = gr.Button("清除条款", variant="secondary")
            rag_query = gr.Textbox(label="提问", placeholder="例如：免赔额怎么算、等待期多久")
            rag_btn = gr.Button("发送", variant="primary")
            rag_answer = gr.Markdown(label="答案")
            rag_meta = gr.Textbox(label="溯源与轮数", lines=3)

            def do_upload(file, token, session_id):
                msg, sid, fn = _upload_clause(file, token, session_id or "")
                if fn:
                    status = f"📄 已加载：{fn}"
                else:
                    status = msg if "已加载" not in msg else msg
                return msg, sid or _gen_session_id(), status

            def do_clear(token, session_id):
                msg, sid = _clear_clause(token, session_id)
                return msg, sid, ""

            rag_upload_btn.click(
                fn=do_upload,
                inputs=[rag_file, rag_token, rag_session_id],
                outputs=[rag_meta, rag_session_id, rag_clause_status],
            )
            rag_clear_btn.click(
                fn=do_clear,
                inputs=[rag_token, rag_session_id],
                outputs=[rag_meta, rag_session_id, rag_clause_status],
            )
            rag_btn.click(
                fn=_chat_rag,
                inputs=[rag_user_id, rag_query, rag_token, rag_session_id],
                outputs=[rag_answer, rag_meta],
            )

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
