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

EXTRACT_INSURANCE_SLOTS_PROMPT = """你是一位百万医疗险核保专家。请分析用户当前提问及历史对话，提取以下 6 大核心要素，并判断是否足以进行精准产品推荐。

## 要素定义
1. age（int）：被保人年龄，单位岁。从对话中推断，如"我45岁"、"孩子3岁"。
2. has_social_security（bool）：是否有城镇职工/城乡居民医保。从"有医保"、"没医保"、"自费"等推断。
3. health_condition（dict）：健康状况子项
   - hospitalization_history（bool）：过去两年是否有住院记录
   - nodule（bool）：是否有器官结节（甲状腺、肺结节等）
   - chronic_disease（bool）：是否有慢性病（高血压、糖尿病等）
4. special_needs（str，可选）：特殊需求，如异地就医、特需病房等。

## 任务
- 从用户当前提问和历史上下文中提取上述要素，未提及的填 null。
- 判断 is_complete：年龄、医保、健康状况（住院史/结节/慢性病至少明确）三项都明确时，为 true；否则为 false。
- 若 is_complete 为 false，生成 guide_question：专业且亲切的追问，需包含"因果关联"说明（如：百万医疗险对年龄和健康要求较高，请问……）。
- 若 is_complete 为 true，生成 search_optimization_query：将要素与用户问题重组为可精准检索的完整问句，便于 RAG 召回。

## 输出格式（严格 JSON，不要 markdown 代码块）
{{
  "age": null 或 整数,
  "has_social_security": null 或 true/false,
  "health_condition": {{
    "hospitalization_history": null 或 true/false,
    "nodule": null 或 true/false,
    "chronic_disease": null 或 true/false
  }},
  "special_needs": null 或 "字符串",
  "is_complete": true 或 false,
  "guide_question": null 或 "追问内容（仅当 is_complete 为 false 时）",
  "search_optimization_query": null 或 "重组后的检索问句（仅当 is_complete 为 true 时）"
}}

## 历史上下文
{context}

## 用户当前提问
{query}

请直接输出 JSON："""


def extract_insurance_slots(
    query: str,
    context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    针对百万医疗险，提取 6 大核心要素，判断完整度，生成引导语或优化检索问句。
    返回格式：
    {
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

    # 规范化输出
    result: Dict[str, Any] = {
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

    if result["is_complete"] and not result["search_optimization_query"]:
        result["search_optimization_query"] = query
    if not result["is_complete"] and not result["guide_question"]:
        result["guide_question"] = (
            "百万医疗险对年龄和健康状况要求较高。请问被保人多大年纪？"
            "是否有医保？过去两年是否有过住院记录或慢性病、结节等情况？"
        )

    return result


def _fallback_extract_result(query: str, is_complete: bool = False) -> Dict[str, Any]:
    """LLM 不可用或解析失败时的兜底"""
    return {
        "age": None,
        "has_social_security": None,
        "health_condition": {
            "hospitalization_history": None,
            "nodule": None,
            "chronic_disease": None,
        },
        "special_needs": None,
        "is_complete": is_complete,
        "guide_question": (
            "百万医疗险对年龄和健康状况要求较高。请问被保人多大年纪？"
            "是否有医保？过去两年是否有过住院记录或慢性病、结节等情况？"
        ) if not is_complete else None,
        "search_optimization_query": query if is_complete else None,
    }
