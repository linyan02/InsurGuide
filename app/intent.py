"""
用户问题意图识别 - 保险场景意图分类
支持多种模式，按业务场景灵活选择：
- rule：规则模式（关键词匹配）
- llm：LLM 模式（大模型直接分类）
- llm_vector：LLM + 向量库意图规则
- bert：自训练 BERT 模型 API（独立服务器），超时/失败时走兜底策略
"""
import re
from typing import Dict, Any, List, Tuple, Optional

from config import settings

# 模式常量
MODE_RULE = "rule"
MODE_LLM = "llm"
MODE_LLM_VECTOR = "llm_vector"
MODE_BERT = "bert"
INTENT_MODES = [MODE_RULE, MODE_LLM, MODE_LLM_VECTOR, MODE_BERT]

# 意图枚举（与产品文档「检索/咨询/理赔」等对齐）
INTENT_RETRIEVAL = "retrieval"
INTENT_CONSULTATION = "consultation"
INTENT_CLAIMS = "claims"
INTENT_UNDERWRITING = "underwriting"
INTENT_PRODUCT = "product"
INTENT_GREETING = "greeting"
INTENT_OTHER = "other"

ALL_INTENTS = [
    INTENT_RETRIEVAL,
    INTENT_CONSULTATION,
    INTENT_CLAIMS,
    INTENT_UNDERWRITING,
    INTENT_PRODUCT,
    INTENT_GREETING,
    INTENT_OTHER,
]

# 规则模式：意图 -> 关键词/短语列表
INTENT_KEYWORDS: Dict[str, List[str]] = {
    INTENT_CLAIMS: [
        "理赔", "赔付", "报销", "索赔", "理赔条件", "理赔流程", "理赔材料",
        "报案", "理赔款", "拒赔", "理赔时效", "理赔申请",
    ],
    INTENT_UNDERWRITING: [
        "核保", "健康告知", "除外", "加费", "拒保", "延期", "甲状腺", "结节",
        "乙肝", "高血压", "糖尿病", "核保规则", "智能核保", "人工核保",
    ],
    INTENT_PRODUCT: [
        "保费", "多少钱", "价格", "费率", "保障范围", "保额", "产品对比",
        "哪款", "推荐", "哪种好", "重疾险", "医疗险", "寿险", "意外险",
    ],
    INTENT_RETRIEVAL: [
        "条款", "规定", "定义", "什么是", "如何界定", "等待期", "免责",
        "责任", "范围", "哪些", "什么情况", "符合", "满足", "条件",
    ],
    INTENT_GREETING: [
        "你好", "您好", "嗨", "在吗", "在不在", "hello", "hi", "早上好", "晚上好",
    ],
    INTENT_CONSULTATION: [
        "建议", "合适吗", "能不能", "可以吗", "怎么办", "如何", "怎样",
        "有没有", "是否", "能不能买", "值得", "划算",
    ],
}


# ---------- 规则模式：纯关键词 ----------
def recognize_rule(query: str) -> Dict[str, Any]:
    """
    规则模式：基于关键词匹配识别意图。
    无外部依赖，适合低延迟、无 API 场景。
    返回 {"intent", "confidence", "method": "rule"}
    """
    intent, conf = _rule_based_intent(query)
    return {"intent": intent, "confidence": conf, "method": MODE_RULE}


def _rule_based_intent(query: str) -> Tuple[str, float]:
    """基于关键词的意图识别，返回 (intent, confidence)"""
    q = (query or "").strip()
    if not q:
        return INTENT_OTHER, 0.0
    q_lower = q.lower()
    if len(q) <= 6 and any(h in q_lower for h in ["你好", "您好", "hi", "在吗"]):
        return INTENT_GREETING, 0.9
    scores: Dict[str, float] = {i: 0.0 for i in ALL_INTENTS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[intent] += 1.0
                if len(kw) >= 3:
                    scores[intent] += 0.3
    best = max(scores.items(), key=lambda x: x[1])
    if best[1] > 0:
        conf = min(0.95, 0.5 + best[1] * 0.15)
        return best[0], round(conf, 2)
    if len(q) >= 4:
        return INTENT_CONSULTATION, 0.5
    return INTENT_OTHER, 0.4


# ---------- LLM 模式：纯大模型 ----------
def recognize_llm(query: str) -> Dict[str, Any]:
    """
    LLM 模式：由大模型直接输出意图标签。
    需要配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY。
    返回 {"intent", "confidence", "method": "llm"}
    """
    from app.llm_short import call as llm_call

    intent, conf = _llm_intent(query, extra_rules_text=None, llm_call=llm_call)
    return {"intent": intent, "confidence": conf, "method": MODE_LLM}


def _llm_intent(
    query: str,
    extra_rules_text: Optional[str] = None,
    llm_call=None,
) -> Tuple[str, float]:
    """LLM 判断意图，可注入规则文本（用于 llm_vector）"""
    if llm_call is None:
        from app.llm_short import call as llm_call
    base_prompt = """你是一个保险领域意图分类器。请判断用户问题的意图，只输出以下 exactly 一个标签，不要任何解释或标点。
可选标签：retrieval, consultation, claims, underwriting, product, greeting, other
- retrieval: 查条款、规则、定义、等待期、免责等
- consultation: 一般咨询、建议、是否合适、怎么办
- claims: 理赔条件、流程、材料、赔付、报销
- underwriting: 核保、健康告知、除外、加费、疾病核保
- product: 保费、价格、产品对比、保障范围、哪款好
- greeting: 问候、寒暄
- other: 其他
"""
    if extra_rules_text:
        base_prompt += f"\n参考以下意图规则（来自知识库）：\n{extra_rules_text}\n"
    base_prompt += f"\n用户问题：{query}\n标签："
    out = llm_call(base_prompt, max_tokens=20)
    if not out:
        return INTENT_OTHER, 0.4
    out = out.strip().lower().split()[0] if out.split() else out
    out = re.sub(r"[^\w]", "", out)
    if out in ALL_INTENTS:
        return out, 0.85
    return INTENT_OTHER, 0.5


# ---------- BERT 模型 API 模式（自训练模型独立部署，带兜底） ----------
def recognize_bert(query: str) -> Dict[str, Any]:
    """
    调用自训练 BERT 意图分类 API（部署在独立服务器）。
    若请求超时或失败，则使用兜底策略（默认规则模式），保证可用性。
    返回 {"intent", "confidence", "method": "bert"|"bert_fallback", "fallback_reason": optional}
    """
    api_url = getattr(settings, "BERT_INTENT_API_URL", None) or ""
    timeout = getattr(settings, "BERT_INTENT_TIMEOUT", 2.0)
    fallback_mode = (getattr(settings, "BERT_INTENT_FALLBACK_MODE", "rule") or "rule").lower()

    if not api_url or not (query or "").strip():
        result = _intent_fallback(query, fallback_mode)
        result["method"] = "bert_fallback"
        result["fallback_reason"] = "api_url_empty_or_query_empty"
        return result

    ok, intent, confidence, err_msg = _call_bert_intent_api(query, api_url, timeout)
    if ok and intent is not None:
        intent = _normalize_bert_intent(intent)
        return {"intent": intent, "confidence": confidence, "method": MODE_BERT}
    result = _intent_fallback(query, fallback_mode)
    result["method"] = "bert_fallback"
    result["fallback_reason"] = err_msg or "unknown"
    return result


def _call_bert_intent_api(
    query: str,
    api_url: str,
    timeout: float,
) -> Tuple[bool, Optional[str], float, Optional[str]]:
    """
    调用 BERT 意图 API。约定请求/响应格式（可适配）：
    请求: POST JSON {"text": query} 或 {"query": query}
    响应: {"intent": "claims", "confidence": 0.95} 或 {"label": "claims", "score": 0.95}
    返回 (成功?, intent, confidence, 错误信息)
    """
    try:
        import httpx
        payload = {"text": query.strip()}
        if getattr(settings, "BERT_INTENT_REQUEST_QUERY_KEY", None):
            key = settings.BERT_INTENT_REQUEST_QUERY_KEY
            payload = {key: query.strip()}
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(api_url, json=payload)
    except httpx.TimeoutException:
        return False, None, 0.0, "timeout"
    except Exception as e:
        return False, None, 0.0, str(e)

    if resp.status_code != 200:
        return False, None, 0.0, f"http_{resp.status_code}"
    try:
        data = resp.json()
    except Exception:
        return False, None, 0.0, "invalid_json"
    intent = data.get("intent") or data.get("label") or data.get("class")
    conf = data.get("confidence")
    if conf is None:
        conf = data.get("score") or data.get("probability") or 0.8
    try:
        conf = float(conf)
    except (TypeError, ValueError):
        conf = 0.8
    if not intent:
        return False, None, 0.0, "no_intent_in_response"
    return True, str(intent).strip(), conf, None


def _normalize_bert_intent(intent: str) -> str:
    """将 BERT 返回的标签归一化为 ALL_INTENTS 之一"""
    intent = (intent or "").strip().lower()
    intent = re.sub(r"[^\w]", "", intent)
    if intent in ALL_INTENTS:
        return intent
    return INTENT_OTHER


def _intent_fallback(query: str, fallback_mode: str) -> Dict[str, Any]:
    """超时/失败时的兜底：按配置调用 rule 或 llm"""
    if fallback_mode == MODE_LLM:
        return recognize_llm(query)
    return recognize_rule(query)


# ---------- LLM + 向量库规则模式 ----------
def recognize_llm_vector(query: str) -> Dict[str, Any]:
    """
    LLM + 向量库规则模式：先从向量库检索与当前问题相似的意图规则，
    再将规则作为上下文交给 LLM 判断意图。适合规则可配置、可热更新的场景。
    返回 {"intent", "confidence", "method": "llm_vector"}
    若向量库不可用或无规则，则退化为 recognize_llm。
    """
    from app.llm_short import call as llm_call
    from app.vector_db import vector_db

    collection_name = getattr(settings, "INTENT_RULES_COLLECTION", "intent_rules")
    top_k = getattr(settings, "INTENT_VECTOR_TOP_K", 5)
    extra_rules_text = None
    if vector_db.client is not None:
        res = vector_db.query_collection(
            collection_name=collection_name,
            query_texts=[query],
            n_results=top_k,
        )
        if res and res.get("documents") and res["documents"][0]:
            docs = res["documents"][0]
            if docs:
                extra_rules_text = "\n".join(docs[:top_k])
    intent, conf = _llm_intent(query, extra_rules_text=extra_rules_text, llm_call=llm_call)
    return {"intent": intent, "confidence": conf, "method": MODE_LLM_VECTOR}


# ---------- 统一入口：按模式调度 ----------
def recognize(query: str, mode: Optional[str] = None) -> Dict[str, Any]:
    """
    意图识别统一入口。mode 为空时使用配置 INTENT_MODE。
    返回 {"intent", "confidence", "method"}
    """
    m = (mode or getattr(settings, "INTENT_MODE", MODE_RULE)).lower()
    if m == MODE_LLM:
        return recognize_llm(query)
    if m == MODE_LLM_VECTOR:
        return recognize_llm_vector(query)
    if m == MODE_BERT:
        return recognize_bert(query)
    return recognize_rule(query)


def get_intent_label_cn(intent: str) -> str:
    """意图中文展示名"""
    labels = {
        INTENT_RETRIEVAL: "条款/规则检索",
        INTENT_CONSULTATION: "一般咨询",
        INTENT_CLAIMS: "理赔",
        INTENT_UNDERWRITING: "核保",
        INTENT_PRODUCT: "产品咨询",
        INTENT_GREETING: "问候",
        INTENT_OTHER: "其他",
    }
    return labels.get(intent, intent)
