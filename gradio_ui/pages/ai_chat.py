"""
AI 对话页：直连 LLM（不经过 RAG），可选能力

依赖 LangChain + OPENAI_API_KEY，独立于后端增强 RAG，便于后续替换或关闭。
"""
import os
import gradio as gr

# 延迟初始化 LLM，避免包加载时强依赖
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
    return None


def _respond(message: str, history: list) -> tuple:
    llm = _get_llm()
    if llm is None:
        return "", history + [(message, "LangChain 未初始化，请设置 OPENAI_API_KEY 环境变量")]
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


def render():
    """渲染「AI 对话」Tab。"""
    with gr.Tab("💬 AI 对话"):
        gr.Markdown("### 与 AI 保险顾问对话")
        chatbot = gr.Chatbot(label="对话历史")
        msg = gr.Textbox(label="输入消息", placeholder="请输入您的问题...")
        clear_btn = gr.Button("清空对话")
        msg.submit(_respond, [msg, chatbot], [msg, chatbot])
        clear_btn.click(lambda: None, None, chatbot, queue=False)
