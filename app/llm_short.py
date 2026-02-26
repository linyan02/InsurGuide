"""
短文本 LLM 调用 - 供意图识别、问题改写等场景使用（小 token、低延迟）
与 answer_engine 的长答案生成解耦，便于按业务选择调用方式

含 extract_insurance_slots：百万医疗险要素提取与引导语生成
"""
import json
import re
from typing import Any, Dict, List, Optional

from config import settings


def call(prompt: str, max_tokens: int = 128) -> str:
    """
    调用大模型生成短文本（意图标签、改写句等）。
    使用与 answer_engine 相同的 API 配置（DASHSCOPE / OpenAI）。
    无可用 API 时返回空字符串。
    """
    try:
        import httpx
        # 优先用通义千问，若配置了 OpenAI 且 key 以 sk- 开头则走 OpenAI 地址
        api_key = getattr(settings, "DASHSCOPE_API_KEY", None) or getattr(
            settings, "OPENAI_API_KEY", None
        )
        if not api_key:
            return ""
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        if getattr(settings, "OPENAI_API_KEY", None) and (
            (settings.OPENAI_API_KEY or "").startswith("sk-")
        ):
            url = "https://api.openai.com/v1/chat/completions"
            api_key = settings.OPENAI_API_KEY
        body = {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if "openai.com" in url:
            body["model"] = "gpt-3.5-turbo"
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            return (msg.get("content") or "").strip()
    except Exception:
        pass
    return ""


def is_available() -> bool:
    """是否有可用的短文本 LLM API"""
    return bool(
        getattr(settings, "DASHSCOPE_API_KEY", None)
        or getattr(settings, "OPENAI_API_KEY", None)
    )


# ---------- 百万医疗险要素提取与引导 ----------

# 用户需求类型：product_overview=只想了解产品列表，personalized_recommendation=需要按个人情况推荐，ambiguous=需先澄清
NEED_TYPE_PRODUCT_OVERVIEW = "product_overview"
NEED_TYPE_PERSONALIZED = "personalized_recommendation"
NEED_TYPE_AMBIGUOUS = "ambiguous"

EXTRACT_INSURANCE_SLOTS_PROMPT = """你是一位百万医疗险顾问。请先判断用户真实需求，再决定是直接回答还是收集个人信息。

## 第一步：判断用户需求类型（need_type）
- **product_overview**：用户只想了解产品（如"有哪些产品""产品有哪些""介绍一下百万医疗"），不需要个人推荐。特征：问产品列表、想先看看、了解有哪些。
- **personalized_recommendation**：用户需要根据年龄/健康状况等推荐。特征：问"推荐""适合我""买哪款""我xx岁能买吗"等，或已提供年龄/健康状况。
- **ambiguous**：意图不明，无法区分。如仅说"百万医疗""百万医疗有哪些产品"且无上下文澄清。

## 第二步：按 need_type 处理
- 若 need_type 为 **product_overview**：is_complete=true，search_optimization_query=用户问题（如"百万医疗有哪些产品"），不追问。
- 若 need_type 为 **ambiguous**：is_complete=false，guide_question 为澄清问题："咱们先确认一下，您是想先了解一下市面上有哪些百万医疗产品，还是想根据您的年龄、健康状况等情况，帮您推荐适合的？"（语气亲切口语化）
- 若 need_type 为 **personalized_recommendation**：按下方要素提取逻辑处理。

## 第三步：个性化推荐时的要素提取（仅 need_type=personalized_recommendation 时执行）
要素定义：
1. age（int）：被保人年龄。2. has_social_security（bool）：是否有医保。
3. health_condition：hospitalization_history、nodule、chronic_disease。
4. special_needs（str，可选）。

- 年龄、医保、健康状况（住院史/结节/慢性病至少明确）三项都明确 → is_complete=true，生成 search_optimization_query。
- 否则 → is_complete=false，生成 guide_question，亲切追问（如：百万医疗对年龄和健康有要求，请问被保人多大了？是否有医保？过去两年有住院或结节、慢性病吗？）。

## 历史上下文（重要）
若上一轮是您向用户提问"您是想了解产品还是根据情况推荐"，用户回答"了解产品""先看看""有哪些"等 → need_type=product_overview，is_complete=true。
用户回答"推荐""帮我选""根据我的情况"等 → need_type=personalized_recommendation，继续要素提取。

## 输出格式（严格 JSON，不要 markdown 代码块）
{{
  "need_type": "product_overview" 或 "personalized_recommendation" 或 "ambiguous",
  "age": null 或 整数,
  "has_social_security": null 或 true/false,
  "health_condition": {{ "hospitalization_history": null, "nodule": null, "chronic_disease": null }},
  "special_needs": null 或 "字符串",
  "is_complete": true 或 false,
  "guide_question": null 或 "追问/澄清内容",
  "search_optimization_query": null 或 "检索问句"
}}

## 历史上下文
{context}

## 用户当前提问
{query}

请直接输出 JSON："""


# 需求澄清时的标准追问（意图不明时先确认用户是想了解产品还是需要推荐）
CLARIFY_NEED_QUESTION = (
    "咱们先确认一下：您是想先了解一下市面上有哪些百万医疗产品，"
    "还是想根据您的年龄、健康状况等情况，帮您推荐适合的？"
)


def extract_insurance_slots(
    query: str,
    context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    针对百万医疗险，先判断用户需求类型（了解产品 vs 个性化推荐），再提取要素。
    返回格式：
    {
      "need_type": "product_overview" | "personalized_recommendation" | "ambiguous",
      "age": int|null,
      "has_social_security": bool|null,
      "health_condition": {...},
      "special_needs": str|null,
      "is_complete": bool,
      "guide_question": str|null,
      "search_optimization_query": str|null,
    }
    """
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"
    prompt = EXTRACT_INSURANCE_SLOTS_PROMPT.format(
        context=context_str,
        query=query.strip(),
    )
    raw = call(prompt, max_tokens=512)
    if not raw:
        return _fallback_extract_result(query, is_complete=False)

    # 解析 JSON（可能被 markdown 包裹）
    text = raw.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_extract_result(query, is_complete=False)

    if not isinstance(data, dict):
        return _fallback_extract_result(query, is_complete=False)

    need_type = (data.get("need_type") or "").strip() or NEED_TYPE_AMBIGUOUS
    if need_type not in (NEED_TYPE_PRODUCT_OVERVIEW, NEED_TYPE_PERSONALIZED, NEED_TYPE_AMBIGUOUS):
        need_type = NEED_TYPE_AMBIGUOUS

    # 规范化输出
    result: Dict[str, Any] = {
        "need_type": need_type,
        "age": data.get("age"),
        "has_social_security": data.get("has_social_security"),
        "health_condition": data.get("health_condition") or {
            "hospitalization_history": None,
            "nodule": None,
            "chronic_disease": None,
        },
        "special_needs": data.get("special_needs"),
        "is_complete": bool(data.get("is_complete")),
        "guide_question": data.get("guide_question"),
        "search_optimization_query": data.get("search_optimization_query"),
    }

    # need_type 为 product_overview 时：直接回答产品问题，无需收集个人信息
    if need_type == NEED_TYPE_PRODUCT_OVERVIEW:
        result["is_complete"] = True
        result["search_optimization_query"] = result["search_optimization_query"] or query
        result["guide_question"] = None

    # need_type 为 ambiguous 时：先用澄清问题引导
    elif need_type == NEED_TYPE_AMBIGUOUS:
        result["is_complete"] = False
        result["guide_question"] = result["guide_question"] or CLARIFY_NEED_QUESTION
        result["search_optimization_query"] = None

    # need_type 为 personalized_recommendation 时：按原有要素逻辑
    else:
        if result["is_complete"] and not result["search_optimization_query"]:
            result["search_optimization_query"] = query
        if not result["is_complete"] and not result["guide_question"]:
            result["guide_question"] = (
                "百万医疗险对年龄和健康状况要求较高。请问被保人多大年纪？"
                "是否有医保？过去两年是否有过住院记录或慢性病、结节等情况？"
            )

    return result


def _fallback_extract_result(query: str, is_complete: bool = False) -> Dict[str, Any]:
    """LLM 不可用或解析失败时的兜底。默认用澄清问题，避免直接问年龄健康。"""
    return {
        "need_type": NEED_TYPE_AMBIGUOUS,
        "age": None,
        "has_social_security": None,
        "health_condition": {
            "hospitalization_history": None,
            "nodule": None,
            "chronic_disease": None,
        },
        "special_needs": None,
        "is_complete": is_complete,
        "guide_question": CLARIFY_NEED_QUESTION if not is_complete else None,
        "search_optimization_query": query if is_complete else None,
    }
