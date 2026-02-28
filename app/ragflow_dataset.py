"""
RAGflow 知识库与文档管理 - 用于用户条款上传

调用 RAGflow API 创建用户条款专用知识库、上传文档、轮询解析状态。
"""
import time
from typing import Any, Dict, List

import httpx

from config import settings


def _base_url() -> str:
    """获取 RAGflow API 基础 URL（不含 /retrieval）。"""
    url = (settings.RAGFLOW_API_URL or "").rstrip("/")
    if "/retrieval" in url:
        url = url.replace("/retrieval", "")
    if url and not url.endswith("/api/v1"):
        url = url.rstrip("/") + "/api/v1"
    return url


def _headers() -> Dict[str, str]:
    """JSON 请求的通用请求头。"""
    headers = {"Content-Type": "application/json"}
    key = getattr(settings, "RAGFLOW_API_KEY", None)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    return headers


def create_clause_dataset(name: str) -> Dict[str, Any]:
    """
    创建用户条款专用知识库。
    chunk_method 使用 "laws" 或 "naive"，适合条款类文档。
    """
    base = _base_url()
    if not base:
        return {"error": "RAGflow API 未配置"}
    url = base + "/datasets"
    chunk_method = getattr(settings, "CLAUSE_KB_CHUNK_METHOD", "naive")
    if chunk_method not in ("laws", "naive", "book"):
        chunk_method = "naive"
    payload = {"name": name, "chunk_method": chunk_method}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=_headers())
    except Exception as e:
        return {"error": f"创建知识库异常: {e}"}
    if resp.status_code != 200:
        return {"error": f"创建知识库失败: HTTP {resp.status_code}"}
    try:
        data = resp.json()
    except Exception:
        return {"error": "创建知识库返回非 JSON"}
    if data.get("code") != 0:
        return {"error": data.get("message", "创建知识库失败")}
    inner = data.get("data")
    dataset_id = inner.get("id") if isinstance(inner, dict) else None
    if not dataset_id:
        return {"error": "创建知识库未返回 ID"}
    return {"dataset_id": dataset_id, "name": name}


def upload_document(
    dataset_id: str, file_content: bytes, file_name: str
) -> Dict[str, Any]:
    """
    上传文档到指定知识库。
    file_content: 文件二进制内容
    file_name: 文件名（含扩展名）
    """
    base = _base_url()
    if not base:
        return {"error": "RAGflow API 未配置"}
    url = base + f"/datasets/{dataset_id}/documents"
    headers = {}
    key = getattr(settings, "RAGFLOW_API_KEY", None)
    if key:
        headers["Authorization"] = f"Bearer {key}"
    files = {"file": (file_name or "upload.pdf", file_content)}
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, files=files, headers=headers)
    except Exception as e:
        return {"error": f"上传异常: {e}"}
    if resp.status_code != 200:
        return {"error": f"上传失败: HTTP {resp.status_code}"}
    try:
        data = resp.json()
    except Exception:
        return {"error": "上传返回非 JSON"}
    if data.get("code") != 0:
        return {"error": data.get("message", "上传失败")}
    doc_list = data.get("data")
    if not isinstance(doc_list, list):
        doc_list = [doc_list] if doc_list else []
    doc_ids = [d.get("id") for d in doc_list if isinstance(d, dict) and d.get("id")]
    return {"document_ids": doc_ids, "dataset_id": dataset_id}


def parse_documents(dataset_id: str, document_ids: List[str]) -> Dict[str, Any]:
    """触发文档解析。"""
    base = _base_url()
    if not base:
        return {"error": "RAGflow API 未配置"}
    url = base + f"/datasets/{dataset_id}/chunks"
    payload = {"document_ids": document_ids}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=_headers())
    except Exception as e:
        return {"error": f"解析请求异常: {e}"}
    if resp.status_code != 200:
        return {"error": f"解析请求失败: HTTP {resp.status_code}"}
    try:
        data = resp.json()
    except Exception:
        return {"error": "解析请求返回非 JSON"}
    if data.get("code") != 0:
        return {"error": data.get("message", "解析请求失败")}
    return {"ok": True}


def wait_for_parsing(
    dataset_id: str, document_ids: List[str], max_wait: int = 120
) -> bool:
    """
    轮询文档解析状态，直到完成或超时。
    run: 0=UNSTART, 1=RUNNING, 3=DONE, 4=FAIL
    """
    base = _base_url()
    if not base:
        return False
    url = base + f"/datasets/{dataset_id}/documents"
    doc_id_set = set(document_ids)
    start = time.time()
    while time.time() - start < max_wait:
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    url + "?page=1&page_size=100", headers=_headers()
                )
        except Exception:
            time.sleep(3)
            continue
        if resp.status_code != 200:
            time.sleep(3)
            continue
        try:
            data = resp.json()
        except Exception:
            time.sleep(3)
            continue
        if data.get("code") != 0:
            time.sleep(3)
            continue
        docs = data.get("data") or []
        all_done = True
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            if doc.get("id") not in doc_id_set:
                continue
            run = doc.get("run", 0)
            if run == 4:
                return False
            if run in (0, 1):
                all_done = False
                break
        if all_done:
            return True
        time.sleep(5)
    return False
