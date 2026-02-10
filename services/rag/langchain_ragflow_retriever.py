"""
LangChain RAGflow Retriever：将 RAGflow 检索封装为 LangChain BaseRetriever

便于在 LangChain RAG 链中统一使用 RAGflow 作为检索源，与 Chroma Retriever 并列多路召回。
"""
from typing import List, Optional

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from services.rag._ragflow import call_ragflow


class RAGflowRetriever(BaseRetriever):
    """
    自定义 Retriever：内部调用现有 call_ragflow，返回 LangChain Document 列表。
    """

    top_k: int = 5
    """每次检索返回的最大片段数。"""

    knowledge_base_id: Optional[str] = None
    """RAGflow 知识库 ID，不传则用配置中的 RAGFLOW_KNOWLEDGE_BASE_ID。"""

    def _get_relevant_documents(self, query: str) -> List[Document]:
        res = call_ragflow(query, top_k=self.top_k, knowledge_base_id=self.knowledge_base_id)
        if "error" in res:
            return []
        docs = res.get("documents") or []
        metas = res.get("metadatas") or []
        result: List[Document] = []
        for i, content in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            result.append(
                Document(
                    page_content=str(content),
                    metadata=dict(meta),
                )
            )
        return result
