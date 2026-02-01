"""
Gradio 应用
提供 Web UI 界面
"""
import gradio as gr
from config import settings
import requests
import os

# API 基础 URL
API_BASE_URL = "http://localhost:8000"

# 初始化 LangChain (需要设置 OPENAI_API_KEY 环境变量)
llm = None
try:
    from langchain_openai import ChatOpenAI
    from langchain.chains import LLMChain
    from langchain.prompts import PromptTemplate
    
    if os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(temperature=0.7, model_name="gpt-3.5-turbo")
except ImportError:
    try:
        from langchain.llms import OpenAI
        if os.getenv("OPENAI_API_KEY"):
            llm = OpenAI(temperature=0.7)
    except ImportError:
        print("LangChain 未安装或版本不兼容")
except Exception as e:
    print(f"LangChain 初始化失败: {str(e)}")


def login(username: str, password: str):
    """登录功能"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            return f"登录成功！Token: {token[:20]}..."
        else:
            return f"登录失败: {response.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"登录错误: {str(e)}"


def register(username: str, email: str, password: str):
    """注册功能"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password
            }
        )
        if response.status_code == 201:
            return "注册成功！"
        else:
            return f"注册失败: {response.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"注册错误: {str(e)}"


def query_vector_db(query_text: str, n_results: int = 5, token: str = ""):
    """查询向量数据库"""
    if not token:
        return "请先登录获取 Token"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{API_BASE_URL}/api/vector/query",
            json={
                "query_texts": [query_text],
                "n_results": n_results
            },
            headers=headers
        )
        if response.status_code == 200:
            results = response.json()["results"]
            return f"查询结果: {results}"
        else:
            return f"查询失败: {response.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"查询错误: {str(e)}"


def search_es(index: str, query_text: str, token: str = ""):
    """搜索 Elasticsearch"""
    if not token:
        return "请先登录获取 Token"
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{API_BASE_URL}/api/es/search",
            json={
                "index": index,
                "query": {
                    "match": {
                        "_all": query_text
                    }
                }
            },
            headers=headers
        )
        if response.status_code == 200:
            results = response.json()["results"]
            return f"搜索结果: {results}"
        else:
            return f"搜索失败: {response.json().get('detail', '未知错误')}"
    except Exception as e:
        return f"搜索错误: {str(e)}"


def chat_with_llm(message: str, history: list):
    """与 LLM 对话"""
    if llm is None:
        return "LangChain 未初始化，请设置 OPENAI_API_KEY 环境变量"
    
    try:
        from langchain.chains import LLMChain
        from langchain.prompts import PromptTemplate
        
        prompt = PromptTemplate(
            input_variables=["question"],
            template="你是一个专业的保险顾问。请回答以下问题：{question}"
        )
        chain = LLMChain(llm=llm, prompt=prompt)
        response = chain.run(message)
        return response
    except Exception as e:
        return f"LLM 错误: {str(e)}"


# 创建 Gradio 界面
with gr.Blocks(title="InsurGuide - 智能保险指南系统") as demo:
    gr.Markdown("# 🛡️ InsurGuide - 智能保险指南系统")
    gr.Markdown("基于 FastAPI、LangChain 和 Gradio 构建的智能保险指南平台")
    
    with gr.Tabs():
        # 认证标签页
        with gr.Tab("🔐 用户认证"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 登录")
                    login_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                    login_password = gr.Textbox(label="密码", type="password", placeholder="请输入密码")
                    login_btn = gr.Button("登录", variant="primary")
                    login_output = gr.Textbox(label="登录结果", lines=3)
                    
                    login_btn.click(
                        fn=login,
                        inputs=[login_username, login_password],
                        outputs=login_output
                    )
                
                with gr.Column():
                    gr.Markdown("### 注册")
                    reg_username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                    reg_email = gr.Textbox(label="邮箱", placeholder="请输入邮箱")
                    reg_password = gr.Textbox(label="密码", type="password", placeholder="请输入密码")
                    reg_btn = gr.Button("注册", variant="primary")
                    reg_output = gr.Textbox(label="注册结果", lines=3)
                    
                    reg_btn.click(
                        fn=register,
                        inputs=[reg_username, reg_email, reg_password],
                        outputs=reg_output
                    )
        
        # 向量数据库标签页
        with gr.Tab("🔍 向量数据库"):
            gr.Markdown("### 查询向量数据库")
            vector_token = gr.Textbox(label="Token", placeholder="请输入登录后获取的 Token")
            vector_query = gr.Textbox(label="查询文本", placeholder="请输入要查询的内容")
            vector_n_results = gr.Slider(minimum=1, maximum=20, value=5, label="返回结果数量")
            vector_btn = gr.Button("查询", variant="primary")
            vector_output = gr.Textbox(label="查询结果", lines=10)
            
            vector_btn.click(
                fn=query_vector_db,
                inputs=[vector_query, vector_n_results, vector_token],
                outputs=vector_output
            )
        
        # Elasticsearch 标签页
        with gr.Tab("📊 Elasticsearch"):
            gr.Markdown("### 搜索 Elasticsearch")
            es_token = gr.Textbox(label="Token", placeholder="请输入登录后获取的 Token")
            es_index = gr.Textbox(label="索引名称", placeholder="请输入索引名称", value="insurguide")
            es_query = gr.Textbox(label="搜索文本", placeholder="请输入要搜索的内容")
            es_btn = gr.Button("搜索", variant="primary")
            es_output = gr.Textbox(label="搜索结果", lines=10)
            
            es_btn.click(
                fn=search_es,
                inputs=[es_index, es_query, es_token],
                outputs=es_output
            )
        
        # LLM 对话标签页
        with gr.Tab("💬 AI 对话"):
            gr.Markdown("### 与 AI 保险顾问对话")
            chatbot = gr.Chatbot(label="对话历史")
            msg = gr.Textbox(label="输入消息", placeholder="请输入您的问题...")
            clear = gr.Button("清空对话")
            
            def respond(message, chat_history):
                bot_message = chat_with_llm(message, chat_history)
                chat_history.append((message, bot_message))
                return "", chat_history
            
            msg.submit(respond, [msg, chatbot], [msg, chatbot])
            clear.click(lambda: None, None, chatbot, queue=False)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=settings.GRADIO_PORT,
        share=settings.GRADIO_SHARE
    )
