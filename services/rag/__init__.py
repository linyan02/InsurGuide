"""
增强 RAG 服务包：召回、融合、精排、流水线编排、LangChain 集成

- recall / fusion / rerank：多路召回与精排
- run_chat_pipeline：原有流水线（意图→改写→RAGflow→答案→合规→日志）
- run_chat_with_langchain：LangChain 版流水线（RAGflowRetriever + DashScopeLLM + 可选 Chroma）
- RAGflowRetriever / DashScopeLLM / get_chroma_retriever：LangChain 组件
"""
from services.rag.recall import recall, recall_ragflow_only
from services.rag.fusion import fusion
from services.rag.rerank import rerank
from services.rag.pipeline import run_chat_pipeline
from services.rag.langchain_chain import run_chat_with_langchain
from services.rag.langchain_ragflow_retriever import RAGflowRetriever
from services.rag.langchain_dashscope_llm import DashScopeLLM
from services.rag.langchain_chroma import get_chroma_vectorstore, get_chroma_retriever

__all__ = [
    "recall",
    "recall_ragflow_only",
    "fusion",
    "rerank",
    "run_chat_pipeline",
    "run_chat_with_langchain",
    "RAGflowRetriever",
    "DashScopeLLM",
    "get_chroma_vectorstore",
    "get_chroma_retriever",
]
