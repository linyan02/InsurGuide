"""
医疗条款解析 - 条款上下文管理

条款内容（文本或上传后的知识库 ID）存入 Redis，与对话会话绑定，
用于多轮咨询时优先基于用户提供的条款回答问题。
"""
import json
import time
from typing import Any, Dict, Optional

from config import settings

from core.redis_store import get_redis_client


def _clause_key(user_id: str, session_id: str) -> str:
    sid = session_id or "default"
    return f"clause_ctx:{user_id}:{sid}"


def save_clause_context(
    user_id: str,
    session_id: str,
    source: str,  # "text" | "upload"
    *,
    dataset_id: Optional[str] = None,
    text_preview: Optional[str] = None,
    text_full: Optional[str] = None,  # 粘贴的完整条款文本，用于多轮咨询
    file_name: Optional[str] = None,
) -> None:
    """保存条款上下文到 Redis。"""
    client = get_redis_client()
    if not client:
        return
    key = _clause_key(user_id, session_id)
    data: Dict[str, Any] = {
        "source": source,
        "created_at": int(time.time()),
    }
    if dataset_id:
        data["dataset_id"] = dataset_id
    if text_preview:
        data["text_preview"] = (
            (text_preview[:500] + "...") if len(text_preview) > 500 else text_preview
        )
    if text_full:
        data["text_full"] = text_full
    if file_name:
        data["file_name"] = file_name
    ttl_seconds = getattr(settings, "REDIS_CONTEXT_TTL_MINUTES", 30) * 60
    try:
        client.setex(key, ttl_seconds, json.dumps(data, ensure_ascii=False))
    except Exception as e:
        print(f"保存条款上下文失败: {e}")


def get_clause_context(user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
    """获取当前会话的条款上下文。"""
    client = get_redis_client()
    if not client:
        return None
    key = _clause_key(user_id, session_id)
    try:
        raw = client.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


def clear_clause_context(user_id: str, session_id: str) -> bool:
    """清除条款上下文。"""
    client = get_redis_client()
    if not client:
        return False
    key = _clause_key(user_id, session_id)
    try:
        client.delete(key)
        return True
    except Exception:
        return False


def restore_clause_context(user_id: str, session_id: str, snapshot: Dict[str, Any]) -> bool:
    """
    P2-11：将 clause_snapshot 写回 Redis，恢复历史对话时的条款上下文。
    snapshot 与 clause_ctx 结构一致：source, dataset_id, file_name, text_preview, text_full, created_at。
    若 RAGflow dataset 已删除，source=upload 时可能无法实际恢复检索能力，但 file_name 可展示。
    """
    client = get_redis_client()
    if not client or not snapshot:
        return False
    key = _clause_key(user_id, session_id)
    try:
        data = {k: v for k, v in snapshot.items() if v is not None}
        if not data:
            return False
        data.setdefault("created_at", int(time.time()))
        ttl_seconds = getattr(settings, "REDIS_CONTEXT_TTL_MINUTES", 30) * 60
        client.setex(key, ttl_seconds, json.dumps(data, ensure_ascii=False))
        return True
    except Exception as e:
        print(f"恢复条款上下文失败: {e}")
        return False
