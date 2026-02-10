"""
用户问题改写 - 结合多轮对话上下文，将指代、省略句改写成可独立检索的完整问题
支持三种模式，按业务场景灵活选择：
- rule：规则模式（上文主题补全）
- llm：LLM 模式（大模型直接改写）
- llm_vector：LLM + 向量库改写示例（从向量库检索相似示例作为 LLM 参考）
"""
from typing import Dict, Any, List, Optional

from config import settings

# 模式常量
MODE_RULE = "rule"
MODE_LLM = "llm"
MODE_LLM_VECTOR = "llm_vector"
REWRITE_MODES = [MODE_RULE, MODE_LLM, MODE_LLM_VECTOR]

# 指代/省略触发词
REWRITE_TRIGGERS = [
    "那", "这个", "它", "呢", "还有", "另外", "然后", "接下来",
    "怎么办", "如何", "怎样", "啥", "多少", "多久", "哪些",
]
# 问句长度小于等于此值时，规则模式会尝试用上文主题补全
MIN_QUERY_LEN_FOR_REWRITE = 4


def _extract_topic_from_turn(turn: Dict[str, Any]) -> str:
    """从一轮对话中抽取主题词（优先用用户问句前半句，否则用答案首句），用于规则补全。"""
    q = (turn.get("query") or "").strip()
    a = (turn.get("answer") or "").strip()
    if q:
        for sep in ["，", "。", "？", "?", " "]:
            if sep in q:
                q = q.split(sep)[0]
        return q[:20].strip()
    if a:
        for sep in ["。", "\n", "；"]:
            if sep in a:
                a = a.split(sep)[0]
        return a[:15].strip()
    return ""


# ---------- 规则模式 ----------
def rewrite_rule(query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    规则模式：若问句过短或含指代/省略词，用最近一轮主题补全。
    无外部依赖，适合低延迟、无 API 场景。
    返回 {"rewritten_query", "method": "rule", "changed": bool}
    """
    q = (query or "").strip()
    if not q:
        return {"rewritten_query": q, "method": MODE_RULE, "changed": False}
    rewritten = _rule_based_rewrite(q, context or [])
    return {"rewritten_query": rewritten, "method": MODE_RULE, "changed": rewritten != q}


def _rule_based_rewrite(query: str, context: List[Dict[str, Any]]) -> str:
    """规则改写逻辑：过短或含指代词/省略词时，用上一轮主题拼在问句前。"""
    q = (query or "").strip()
    if not q or not context:
        return q
    # 满足「过短」或「含那/这个/呢/怎么办等」才改写
    need_rewrite = len(q) <= MIN_QUERY_LEN_FOR_REWRITE or any(t in q for t in REWRITE_TRIGGERS)
    if not need_rewrite:
        return q
    topic = _extract_topic_from_turn(context[-1])
    if not topic or topic in q or q in topic:
        return q
    return f"{topic} {q}".strip()


# ---------- LLM 模式 ----------
def rewrite_llm(query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    LLM 模式：由大模型根据对话历史将当前问题改写成完整问句。
    需要配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY。
    返回 {"rewritten_query", "method": "llm", "changed": bool}
    """
    from app.llm_short import call as llm_call

    rewritten = _llm_rewrite_impl(query, context or [], extra_examples=None, llm_call=llm_call)
    changed = (rewritten != query) and (len(rewritten) >= 2)
    return {"rewritten_query": rewritten, "method": MODE_LLM, "changed": changed}


def _llm_rewrite_impl(
    query: str,
    context: List[Dict[str, Any]],
    extra_examples: Optional[str] = None,
    llm_call=None,
) -> str:
    """LLM 改写实现，可注入向量库检索的示例"""
    if llm_call is None:
        from app.llm_short import call as llm_call
    history_str = ""
    if context:
        lines = []
        for i, t in enumerate(context[-5:], 1):
            lines.append(f"Q{i}: {t.get('query', '')}\nA{i}: {(t.get('answer') or '')[:200]}")
        history_str = "\n".join(lines)
    prompt = """根据对话历史，将「当前问题」改写成一句完整、可独立理解的保险相关问题（可补全指代与省略）。只输出改写后的问题，不要解释、不要引号。

对话历史：
"""
    prompt += f"{history_str or '（无）'}\n\n当前问题：{query}\n\n"
    if extra_examples:
        prompt = f"参考以下改写示例（来自知识库）：\n{extra_examples}\n\n" + prompt
    prompt += "改写后问题："
    out = llm_call(prompt, max_tokens=120)
    if out:
        out = out.strip().strip('"').strip("'")
        if len(out) >= 2:
            return out
    return query


# ---------- LLM + 向量库示例模式 ----------
def rewrite_llm_vector(query: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    LLM + 向量库示例模式：先从向量库检索与当前问句/上下文相似的改写示例，
    再将示例作为 few-shot 交给 LLM 改写。适合可配置改写范例、领域定制场景。
    返回 {"rewritten_query", "method": "llm_vector", "changed": bool}
    若向量库不可用或无示例，则退化为 rewrite_llm。
    """
    from app.llm_short import call as llm_call
    from app.vector_db import vector_db

    collection_name = getattr(settings, "REWRITE_RULES_COLLECTION", "rewrite_rules")
    top_k = getattr(settings, "REWRITE_VECTOR_TOP_K", 3)
    extra_examples = None
    if vector_db.client is not None and context:
        # 用「当前问句 + 上一轮主题」作为检索文本，更易命中相似示例
        last_topic = _extract_topic_from_turn(context[-1]) if context else ""
        search_text = f"{last_topic} {query}".strip() or query
        res = vector_db.query_collection(
            collection_name=collection_name,
            query_texts=[search_text],
            n_results=top_k,
        )
        if res and res.get("documents") and res["documents"][0]:
            docs = res["documents"][0]
            if docs:
                extra_examples = "\n".join(docs[:top_k])
    rewritten = _llm_rewrite_impl(
        query, context or [], extra_examples=extra_examples, llm_call=llm_call
    )
    changed = (rewritten != query) and (len(rewritten) >= 2)
    return {"rewritten_query": rewritten, "method": MODE_LLM_VECTOR, "changed": changed}


# ---------- 统一入口：按模式调度 ----------
def rewrite(
    query: str,
    context: List[Dict[str, Any]],
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    问题改写统一入口。mode 为空时使用配置 REWRITE_MODE。
    返回 {"rewritten_query", "method", "changed"}
    """
    q = (query or "").strip()
    if not q:
        return {"rewritten_query": q, "method": "none", "changed": False}
    m = (mode or getattr(settings, "REWRITE_MODE", MODE_RULE)).lower()
    if m == MODE_LLM:
        return rewrite_llm(q, context or [])
    if m == MODE_LLM_VECTOR:
        return rewrite_llm_vector(q, context or [])
    return rewrite_rule(q, context or [])
