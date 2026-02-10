"""
LangChain 集成 Chroma 向量库

本文件演示如何使用 LangChain 自带的 Chroma 封装来访问项目中已有的 ChromaDB 数据。

说明：
- 核心存储仍然是 config.VECTOR_DB_PATH 对应目录下的 ChromaDB，
  与 core.vector_db 中的 PersistentClient 共享同一份磁盘数据。
- 这里通过 LangChain 的 Chroma 封装，得到一个 VectorStore / Retriever，
  便于在 LangChain RAG 链路中直接使用。
"""
from typing import Optional

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

from config import settings


def get_chroma_vectorstore(
    collection_name: Optional[str] = None,
    *,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> Chroma:
    """
    获取一个基于 LangChain 的 Chroma VectorStore。

    参数：
    - collection_name：集合名，默认为 settings.VECTOR_DB_COLLECTION；
      你也可以传 "intent_rules"、"rewrite_rules" 等业务集合名。
    - model_name：用于生成向量的 sentence-transformers 模型名，
      这里默认用多语言通用模型，适合中英文混合场景。

    返回：
    - Chroma VectorStore 实例，可用于 .add_texts / .similarity_search 等。
    """
    coll = collection_name or settings.VECTOR_DB_COLLECTION

    # LangChain 的 Chroma 封装需要一个 embedding_function，这里用 sentence-transformers
    embeddings = SentenceTransformerEmbeddings(model_name=model_name)

    # persist_directory 指向与 core.vector_db 相同的目录，这样可以复用同一份数据
    vectorstore = Chroma(
        collection_name=coll,
        persist_directory=settings.VECTOR_DB_PATH,
        embedding_function=embeddings,
    )
    return vectorstore


def get_chroma_retriever(
    collection_name: Optional[str] = None,
    *,
    k: int = 5,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
):
    """
    获取一个基于 Chroma 的 LangChain Retriever。

    - k：每次检索返回的相似文本数量；
    - 其他参数与 get_chroma_vectorstore 相同。
    """
    vs = get_chroma_vectorstore(collection_name=collection_name, model_name=model_name)
    retriever = vs.as_retriever(search_kwargs={"k": k})
    return retriever

