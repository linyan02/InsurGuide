"""
RAGflow 调用（供 services.rag 召回层使用）

与 app.ragflow_client 功能一致，放在 services 内便于召回层直接依赖，
避免从 app 再引一层。返回 { documents, metadatas } 或 { error }。
"""
from typing import Any, Dict, List, Optional

import httpx

from config import settings


def call_ragflow(
    query: str,
    knowledge_base_id: Optional[str] = None,
    top_k: Optional[int] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """请求 RAGflow 检索接口，返回知识库片段或错误信息。"""
    # 从配置取 API 地址，去掉末尾的 / 避免双斜杠
    base_url = (settings.RAGFLOW_API_URL or "").rstrip("/")
    api_key = settings.RAGFLOW_API_KEY
    kb_id = knowledge_base_id or settings.RAGFLOW_KNOWLEDGE_BASE_ID
    k = top_k if top_k is not None else settings.RAGFLOW_TOP_K
    t = timeout if timeout is not None else settings.RAGFLOW_TIMEOUT
    if not base_url:
        return {"error": "RAGflow API 未配置（RAGFLOW_API_URL）"}
    # RAGflow 官方检索接口：POST /api/v1/retrieval
    request_url = base_url.rstrip("/") + "/retrieval" if not base_url.rstrip("/").endswith("retrieval") else base_url
    if api_key and "knowledge" in base_url.lower():
        payload = {"question": query, "top_k": k, "api_key": api_key}
    else:
        payload = {"question": query, "top_k": k}
    if kb_id:
        payload["dataset_ids"] = [kb_id] if isinstance(kb_id, str) else list(kb_id)
    headers = {"Content-Type": "application/json"}
    if api_key and "api_key" not in payload:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        with httpx.Client(timeout=t) as client:
            resp = client.post(request_url, json=payload, headers=headers)
    except Exception as e:
        return {"error": f"RAGflow 调用异常：{str(e)}"}
    if resp.status_code != 200:
        return {"error": f"RAGflow 调用失败：HTTP {resp.status_code}"}
    try:
        data = resp.json()
    except Exception:
        return {"error": "RAGflow 返回非 JSON"}
    if "error" in data:
        return {"error": data["error"]}
    if data.get("code") is not None and data.get("code") != 0:
        return {"error": data.get("message", "RAGflow 返回错误")}
    # RAGflow 官方 retrieval：data.chunks[]
    if "data" in data:
        inner = data["data"]
        if isinstance(inner, dict) and "chunks" in inner:
            chunks = inner["chunks"] or []
            documents = [c.get("content", "") for c in chunks if isinstance(c, dict)]
            metadatas = [
                {"source": c.get("document_keyword", c.get("document_name", "未知"))}
                for c in chunks if isinstance(c, dict)
            ]
            return _normalize({"documents": documents, "metadatas": metadatas})
        if isinstance(inner, dict):
            return _normalize(inner)
        if isinstance(inner, list):
            return _normalize({"documents": inner})
    if "documents" in data:
        return _normalize(data)
    # 兼容 OpenAI 风格返回：choices[0].message.reference 里带 chunks
    if "choices" in data and len(data["choices"]) > 0:
        msg = data["choices"][0].get("message", {})
        ref = msg.get("reference", {}) or {}
        chunks = ref.get("chunks", ref) if isinstance(ref, dict) else {}
        documents, metadatas = [], []
        for ch in (chunks.values() if isinstance(chunks, dict) else chunks):
            if isinstance(ch, dict):
                documents.append(ch.get("content", ""))
                meta = ch.get("document_metadata") or {}
                metadatas.append(meta if isinstance(meta, dict) else {"source": ch.get("document_name", "未知")})
        return {"documents": documents, "metadatas": metadatas}
    return _normalize(data)


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """将 RAGflow 多种返回结构统一为 { documents, metadatas }，并补齐 metadatas 长度。"""
    # 兼容不同字段名：文档列表可能在 documents 或 chunks
    documents = raw.get("documents") or raw.get("chunks") or []
    metadatas = raw.get("metadatas") or raw.get("metadata") or []
    if isinstance(documents, str):
        documents = [documents]
    if isinstance(metadatas, dict):
        metadatas = [metadatas]
    while len(metadatas) < len(documents):
        metadatas.append({"source": "未知"})
    return {"documents": list(documents)[:50], "metadatas": list(metadatas)[:50]}
