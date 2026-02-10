"""
精排层：对融合后的候选做排序与截断

融合后的片段可能很多，精排按相似度分数（score）排序并只保留前 top_k 条，
减少送入 LLM 的 token 数量并提高相关性。当前实现为按 score 降序取前 k 条。
"""
from typing import Any, Dict, List

from config import settings


def rerank(
    fused: Dict[str, Any],
    top_k: int = 0,
) -> Dict[str, Any]:
    """
    对 fusion 输出按 score 降序排序并截断为 top_k 条；top_k=0 表示不截断。
    返回格式仍为 { documents, metadatas }，与下游答案生成兼容。
    """
    # 若上游传下来的是错误结果，直接原样返回
    if "error" in fused:
        return fused
    # 取出文档列表和元数据列表，没有则用空列表
    documents = fused.get("documents") or []
    metadatas = fused.get("metadatas") or []
    if not documents:
        return fused
    # 截断条数：调用方传了 top_k 用传的，否则用配置里的 RAGFLOW_TOP_K，再没有则 5
    k = top_k or getattr(settings, "RAGFLOW_TOP_K", 5)
    # 把文档和元数据一一对应成 (doc, meta) 的列表，便于按 meta 的 score 排序
    pairs = list(zip(documents, metadatas))
    # 按元数据里的 score 降序排，score 缺省当 0；reverse=True 表示分数高的在前
    pairs.sort(key=lambda x: float(x[1].get("score", 0)), reverse=True)
    # 只保留前 k 条
    pairs = pairs[:k]
    # 再拆回 documents 和 metadatas 两个列表
    new_docs = [p[0] for p in pairs]
    new_metas = [p[1] for p in pairs]
    return {"documents": new_docs, "metadatas": new_metas}
