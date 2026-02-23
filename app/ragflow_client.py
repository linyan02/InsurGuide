"""
RAGflow 调用模块 - 检索知识库
与产品技术文档中的「RAGflow 核心 API」对齐：传入提问 + 知识库 ID，返回匹配文本片段与来源
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
    """
    调用 RAGflow 检索知识库。
    返回格式与产品文档一致：含 documents、metadatas（来源等），或 error 键表示失败。
    """
    base_url = (settings.RAGFLOW_API_URL or "").rstrip("/")
    api_key = settings.RAGFLOW_API_KEY
    kb_id = knowledge_base_id or settings.RAGFLOW_KNOWLEDGE_BASE_ID
    k = top_k if top_k is not None else settings.RAGFLOW_TOP_K
    t = timeout if timeout is not None else settings.RAGFLOW_TIMEOUT

    if not base_url:
        return {"error": "RAGflow API 未配置（RAGFLOW_API_URL）"}
    if not api_key and "/api/v1/" in base_url:
        return {"error": "RAGflow API Key 未配置（RAGFLOW_API_KEY）"}

    # RAGflow 官方检索接口为 POST /api/v1/retrieval，若配置的是 base（如 /api/v1）则自动追加
    request_url = base_url if base_url.rstrip("/").endswith("retrieval") else (base_url + "/retrieval")

    # 请求体：RAGflow 官方约定为 question、dataset_ids（数组）、top_k
    payload: Dict[str, Any] = {
        "question": query,
        "top_k": k,
    }
    if kb_id:
        payload["dataset_ids"] = [kb_id] if isinstance(kb_id, str) else list(kb_id)
    if api_key and _ragflow_uses_api_key_in_body(base_url):
        payload["api_key"] = api_key

    headers = {"Content-Type": "application/json"}
    if api_key and not payload.get("api_key"):
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

    if data.get("code") is not None and data.get("code") != 0:
        return {"error": data.get("message", "RAGflow 返回错误")}

    # 兼容多种返回结构
    if "error" in data:
        return {"error": data["error"]}
    if "data" in data:
        inner = data["data"]
        if isinstance(inner, dict) and "chunks" in inner:
            # RAGflow 官方 retrieval：data.chunks[]，每项含 content、document_keyword 等
            chunks = inner["chunks"] or []
            documents = [c.get("content", "") for c in chunks if isinstance(c, dict)]
            metadatas = [
                {"source": c.get("document_keyword", c.get("document_name", "未知"))}
                for c in chunks if isinstance(c, dict)
            ]
            return _normalize_ragflow_result({"documents": documents, "metadatas": metadatas})
        if isinstance(inner, dict):
            return _normalize_ragflow_result(inner)
        if isinstance(inner, list):
            return _normalize_ragflow_result({"documents": inner})
    if "documents" in data:
        return _normalize_ragflow_result(data)
    # OpenAI 兼容接口返回的 reference 结构
    if "choices" in data and len(data["choices"]) > 0:
        msg = data["choices"][0].get("message", {})
        ref = msg.get("reference", {})
        chunks = ref.get("chunks", ref) if isinstance(ref, dict) else {}
        documents = []
        metadatas = []
        for chunk in (chunks.values() if isinstance(chunks, dict) else chunks):
            if isinstance(chunk, dict):
                documents.append(chunk.get("content", ""))
                meta = chunk.get("document_metadata", chunk.get("document_metadata", {}))
                if isinstance(meta, dict):
                    metadatas.append(meta)
                else:
                    metadatas.append({"source": chunk.get("document_name", "未知")})
        return {"documents": documents, "metadatas": metadatas}

    return _normalize_ragflow_result(data)


def _ragflow_uses_api_key_in_body(base_url: str) -> bool:
    """若为文档中的 /api/v1/knowledge/search 风格，部分实现会在 body 传 api_key"""
    return "knowledge" in base_url.lower()


def _normalize_ragflow_result(raw: Dict[str, Any]) -> Dict[str, Any]:
    """统一为 { documents: [], metadatas: [] }"""
    documents = raw.get("documents") or raw.get("chunks") or []
    metadatas = raw.get("metadatas") or raw.get("metadata") or []
    if isinstance(documents, str):
        documents = [documents]
    if isinstance(metadatas, dict):
        metadatas = [metadatas]
    while len(metadatas) < len(documents):
        metadatas.append({"source": "未知"})
    return {"documents": list(documents)[:50], "metadatas": list(metadatas)[:50]}


def list_knowledge_bases() -> Dict[str, Any]:
    """列举知识库（若 RAGflow 提供 list 接口且已配置）"""
    base_url = (settings.RAGFLOW_API_URL or "").rstrip("/")
    api_key = settings.RAGFLOW_API_KEY
    if not base_url or not api_key:
        return {"error": "RAGflow API 或 API Key 未配置"}
    list_url = base_url.replace("/search", "/list").replace("/v1/search", "/v1/knowledge/list")
    if "/v1/" not in list_url:
        list_url = base_url + "/list"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    try:
        with httpx.Client(timeout=settings.RAGFLOW_TIMEOUT) as client:
            resp = client.get(list_url, headers=headers)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}
        return resp.json()
    except Exception as e:
        return {"error": str(e)}   
