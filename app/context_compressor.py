"""
对话上下文压缩模块 - 筛选与截断历史对话，控制传入 LLM 的 token 量

在答案生成前调用，对 Redis 取出的 context 进行：
1. 关联性筛选（recent_only / hybrid + 关键词相似度）
2. 单轮截断（query/answer 字数限制）
3. Token 预算裁剪
"""
import re
from typing import Any, Dict, List, Optional

from config import settings


def _get(key: str, default: Any) -> Any:
    """配置项（带默认值，避免 settings 未配置时报错）"""
    return getattr(settings, key, default)


def compress_context(
    query: str,
    context: List[Dict[str, Any]],
    *,
    mode: Optional[str] = None,
    rewritten_query: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    对原始 context 进行筛选与压缩，返回可用于答案生成的上下文。

    Args:
        query: 当前用户问题
        context: Redis 取出的完整历史 [{"query":"...", "answer":"..."}, ...]
        mode: 覆盖配置的筛选模式
        rewritten_query: 改写后的问题，用于筛选时计算相似度（可选，更准确）

    Returns:
        筛选并截断后的 [{"query":"...", "answer":"..."}, ...]
    """
    if not _get("CONTEXT_COMPRESSION_ENABLED", True):
        return context

    if not context:
        return []

    selection_mode = mode or _get("CONTEXT_SELECTION_MODE", "hybrid")
    selected = _select_relevant_turns(
        query=rewritten_query or query,
        context=context,
        mode=selection_mode,
    )

    answer_max = _get("CONTEXT_TURN_ANSWER_MAX_CHARS", 150)
    query_max = _get("CONTEXT_TURN_QUERY_MAX_CHARS", 50)
    max_tokens = _get("CONTEXT_MAX_TOKENS", 800)
    recent_required = _get("CONTEXT_RECENT_REQUIRED", 1)

    truncated = [
        _truncate_turn(turn, answer_max, query_max, idx >= len(selected) - recent_required)
        for idx, turn in enumerate(selected)
    ]

    return _apply_token_budget(truncated, max_tokens)


def _select_relevant_turns(
    query: str,
    context: List[Dict[str, Any]],
    mode: str,
) -> List[Dict[str, Any]]:
    """按模式筛选相关轮次。context 按时间从旧到新，返回子集（保持顺序）。"""
    if not context:
        return []

    max_turns = _get("CONTEXT_MAX_TURNS", 5)
    recent_required = _get("CONTEXT_RECENT_REQUIRED", 1)

    if mode == "recent_only":
        return context[-max_turns:]

    if mode == "hybrid" or mode == "similarity":
        recent = context[-recent_required:] if recent_required > 0 else []
        candidate = context[:-recent_required] if recent_required > 0 else context

        if not candidate:
            return recent

        method = _get("CONTEXT_SIMILARITY_METHOD", "keyword")
        scored = []
        for i, turn in enumerate(candidate):
            q = (turn.get("query") or "").strip()
            if not q:
                scored.append((0.0, i, turn))
                continue
            sim = _keyword_similarity(query, q) if method == "keyword" else 0.5
            scored.append((sim, i, turn))

        scored.sort(key=lambda x: (-x[0], -x[1]))
        remain = max(0, max_turns - len(recent))
        selected_turns = [t for _, _, t in scored[:remain]]
        selected_turns.sort(key=lambda t: context.index(t) if t in context else 0)

        return selected_turns + recent

    return context[-max_turns:]


def _keyword_similarity(query: str, turn_query: str) -> float:
    """
    基于关键词/字符重叠的相似度，0~1。
    使用简单分词（按标点、空格切）+ 集合交集 Jaccard。
    """
    def _tokenize(s: str) -> set:
        s = (s or "").strip()
        s = re.sub(r"[，。？！、；：""''\s]+", " ", s)
        return set(w for w in s.split() if len(w) >= 2)

    a, b = _tokenize(query), _tokenize(turn_query)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def _truncate_turn(
    turn: Dict[str, Any],
    answer_max: int,
    query_max: int,
    keep_full: bool = False,
) -> Dict[str, Any]:
    """单轮截断。keep_full=True 时 answer 放宽到 2 倍。"""
    q = (turn.get("query") or "").strip()
    a = (turn.get("answer") or "").strip()

    q_lim = query_max
    a_lim = answer_max * 2 if keep_full else answer_max

    if len(q) > q_lim:
        q = q[:q_lim] + "…"
    if len(a) > a_lim:
        a = a[:a_lim] + "…"

    return {"query": q, "answer": a}


def _apply_token_budget(turns: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
    """
    按 token 预算裁剪。估算：中文约 1 字≈1.5 token，英文 1 词≈1 token。
    从新到旧依次加入，超预算则停止。
    """
    def _est_tokens(s: str) -> int:
        cn = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
        other = len(s) - cn
        return int(cn * 1.5 + other * 0.4)

    result = []
    acc = 0
    for t in reversed(turns):
        q = (t.get("query") or "")
        a = (t.get("answer") or "")
        need = _est_tokens(q) + _est_tokens(a)
        if acc + need > max_tokens and result:
            break
        result.insert(0, t)
        acc += need

    return result
