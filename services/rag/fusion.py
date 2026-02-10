"""
融合层：合并多路召回结果，去重、统一格式

多路召回（如 RAGflow + 本地向量库）会得到多条 [{"content","source","score","origin"}, ...]，
本模块把它们合并成一份 { documents, metadatas }，并按 content 去重，
供精排或直接交给答案生成使用。
"""
from typing import Any, Dict, List


def fusion(recall_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将 recall 层返回的列表融合为 { documents, metadatas }。
    按 content 去重，保留每条 source/score/origin 到 metadatas。
    """
    # 用集合记录已经出现过的 content 文本，避免重复片段进入最终结果
    seen = set()
    documents = []
    metadatas = []
    for item in recall_results:
        # 取出当前条目的正文，空则转成空字符串并 strip
        content = (item.get("content") or "").strip()
        if not content or content in seen:
            continue
        seen.add(content)
        documents.append(content)
        metadatas.append({
            "source": item.get("source", "未知"),
            "score": item.get("score", 1.0),
            "origin": item.get("origin", ""),
        })
    return {"documents": documents, "metadatas": metadatas}


def fusion_from_ragflow_result(ragflow_result: Dict[str, Any]) -> Dict[str, Any]:
    """兼容：若仅 RAGflow 一路且已是 { documents, metadatas }，直接返回；有 error 也原样返回。"""
    if "error" in ragflow_result:
        return ragflow_result
    return ragflow_result
