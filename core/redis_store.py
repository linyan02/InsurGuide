"""
多轮对话上下文 - Redis 缓存

用户连续多轮提问时，需要知道「上一轮问了什么、答了什么」，
才能做问题改写（比如「那理赔呢」要结合上文补全成「重疾险理赔」）。
本模块用 Redis 存每个 user_id 对应的最近 N 轮对话，并设置过期时间，
避免占满内存，也避免用户很久不聊还留着旧上下文。
"""
import json
from datetime import timedelta
from typing import List, Dict, Any, Optional

from config import settings

# 全局只保留一个 Redis 连接，第一次用时再建
_redis_client = None


def _get_redis():
    """获取 Redis 连接。若未连上（没装 Redis 或配置错）返回 None，调用方要能接受。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,  # 取出来的直接是字符串，不用再 .decode()
        )
        _redis_client.ping()  # 测一下是否真的连上了
        return _redis_client
    except Exception as e:
        print(f"⚠ Redis 连接失败: {e}，多轮对话上下文将不可用")
        return None


def save_conversation_context(user_id: str, query: str, answer: str) -> None:
    """
    把本轮「用户问 + 系统答」追加到该用户的对话历史里。
    - Redis 的 key 是 context:用户ID
    - value 是 JSON 数组，每一项是 {"query": "...", "answer": "..."}
    - 超过最大轮数会只保留最近 N 轮；每次写入都会刷新过期时间。
    """
    client = _get_redis()
    if not client:
        return
    key = f"context:{user_id}"
    try:
        raw = client.get(key)
        history = json.loads(raw) if raw else []
        history.append({"query": query, "answer": answer})
        max_turns = getattr(settings, "REDIS_MAX_HISTORY_TURNS", 10)
        if len(history) > max_turns:
            history = history[-max_turns:]  # 只留最近 N 轮
        ttl = timedelta(minutes=getattr(settings, "REDIS_CONTEXT_TTL_MINUTES", 30))
        client.setex(key, ttl, json.dumps(history, ensure_ascii=False))  # setex = 带过期时间的 set
    except Exception as e:
        print(f"保存对话上下文失败: {e}")


def get_conversation_context(user_id: str) -> List[Dict[str, Any]]:
    """
    取出该用户当前的对话历史，用于问题改写和答案生成。
    返回列表，每项形如 {"query": "用户问的", "answer": "系统答的"}。
    没有历史或 Redis 不可用时返回空列表。
    """
    client = _get_redis()
    if not client:
        return []
    key = f"context:{user_id}"
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else []
    except Exception:
        return []


def clear_conversation_context(user_id: str) -> bool:
    """清除该用户的对话历史（例如用户点了「重新开始」）。"""
    client = _get_redis()
    if not client:
        return False
    try:
        client.delete(f"context:{user_id}")
        return True
    except Exception:
        return False
