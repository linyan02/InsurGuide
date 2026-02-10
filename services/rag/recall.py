"""
召回层：多路检索，返回候选片段

「召回」指根据用户问题从多个来源拉取可能相关的文本片段。
当前主路是 RAGflow（远程知识库）；use_local_vector=True 时可同时查本地 ChromaDB，
结果合并为统一格式 [{"content", "source", "score", "origin"}, ...]，供融合层使用。
"""
# 类型注解：Any 表示任意类型，Dict 字典，List 列表，Optional 表示可为 None
from typing import Any, Dict, List, Optional

# 读取配置，例如 VECTOR_DB_COLLECTION、RAGFLOW_TOP_K
from config import settings

# 全局变量，用于缓存 RAGflow 的调用函数；第一次使用时再导入，避免包加载时循环依赖
_ragflow_call = None


def _get_ragflow():
    """获取 RAGflow 调用函数（单例）。首次调用时从 _ragflow 模块导入并缓存。"""
    global _ragflow_call
    if _ragflow_call is None:
        from services.rag._ragflow import call_ragflow
        _ragflow_call = call_ragflow
    return _ragflow_call


def recall(
    query: str,
    top_k: Optional[int] = None,
    use_ragflow: bool = True,
    use_local_vector: bool = False,
    local_collection: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    多路召回，每路返回 [{"content", "source", "score", "origin": "ragflow"|"local_vector"}]
    汇总为列表；当前默认仅 RAGflow，use_local_vector 可扩展本地向量库一路。
    """
    # 初始化结果列表，后面把 RAGflow 和（可选）本地向量库的结果都 append 进来
    results: List[Dict[str, Any]] = []
    if use_ragflow:
        # _get_ragflow() 返回 call_ragflow 函数，再传入 query 和 top_k 执行一次检索
        rag = _get_ragflow()(query, top_k=top_k)
        if "error" not in rag:
            # 取出文档列表和对应的元数据列表
            docs = rag.get("documents") or []
            metas = rag.get("metadatas") or []
            for i, doc in enumerate(docs):
                # 第 i 条文档对应第 i 条元数据，若 metas 长度不够则用空字典
                meta = metas[i] if i < len(metas) else {}
                results.append({
                    "content": doc,
                    "source": meta.get("source", meta.get("document_name", "未知")),
                    "score": meta.get("similarity", 1.0),
                    "origin": "ragflow",
                })
    # 若开启本地向量库一路且指定了集合名（或配置里有默认集合）
    if use_local_vector and (local_collection or settings.VECTOR_DB_COLLECTION):
        from core.vector_db import vector_db
        if vector_db.client is not None:
            coll_name = local_collection or settings.VECTOR_DB_COLLECTION
            res = vector_db.query_collection(
                collection_name=coll_name,
                query_texts=[query],
                n_results=top_k or settings.RAGFLOW_TOP_K,
            )
            # Chroma 返回的 documents 形如 [[doc1, doc2, ...]]，取 res["documents"][0] 才是第一组结果列表
            if res and res.get("documents") and res["documents"][0]:
                for j, doc in enumerate(res["documents"][0]):
                    metadatas = res.get("metadatas") or [[]]
                    meta = (metadatas[0][j] if metadatas and j < len(metadatas[0]) else {}) or {}
                    results.append({
                        "content": doc,
                        "source": meta.get("source", "本地向量库"),
                        "score": 1.0,
                        "origin": "local_vector",
                    })
    return results


def recall_ragflow_only(query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
    """
    仅走 RAGflow 一路召回，返回 { documents, metadatas } 或 { error }，
    与 app.ragflow_client 的返回格式兼容，便于直接交给 answer_engine。
    """
    return _get_ragflow()(query, top_k=top_k)
