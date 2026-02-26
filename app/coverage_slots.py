"""
保障重叠度 Slot 提取 - 从用户问题与上下文中提取现有保障与待购险种

未补全时生成追问语，参考 extract_insurance_slots 实现。
"""
import json
import re
from typing import Any, Dict, List

from app.llm_short import call as llm_call

EXTRACT_COVERAGE_SLOTS_PROMPT = """你是一位保障分析顾问。用户想判断「待购险种」是否与「现有保障」重复。

## 任务
从用户问题与历史对话中提取：
1. existing_coverage_list：已有保障，每项需含 name、deductible、has_outpatient
2. pending_insurance：待购险种名

## 险种名标准化
- 社保/医保/城镇居民医保 → 社保
- 商业补充医疗/公司团险/补充医疗 → 商业补充医疗
- 百万医疗/医疗险(大额) → 百万医疗
- 学平险/学生险 → 学平险
- 意外险/意外伤害险 → 意外险
- 重疾险/重大疾病保险 → 重疾险
- 防癌险/防癌医疗险 → 按给付/报销区分

## 关键变量
- deductible：免赔额，0 或数字（单位元）
- has_outpatient：是否含门诊，true/false

## 输出规则
- 若 existing_coverage_list 或 pending_insurance 缺失 → is_complete=false
- 若「商业补充医疗」存在但 deductible、has_outpatient 任一缺失 → is_complete=false，guide_question 追问
- 追问语气亲切，一次只问 1-2 个关键点

## 历史上下文
{context}

## 用户问题
{query}

## 输出格式（严格 JSON，不要 markdown 代码块）
{{
  "is_complete": true或false,
  "existing_coverage_list": [{{"name":"社保","deductible":null,"has_outpatient":true}}, ...],
  "pending_insurance": "学平险",
  "guide_question": null 或 "追问内容"
}}

请直接输出 JSON："""


FALLBACK_GUIDE_QUESTION = (
    "抱歉，我没完全理解您的保障情况。您能简单列举一下已有的保险吗？"
    "例如：社保、公司团险、百万医疗、学平险等。另外，您打算购买的是哪一种保险？"
)


def extract_coverage_slots(
    query: str,
    context: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    提取保障重叠度分析所需的 Slot。
    返回：
    {
        "is_complete": bool,
        "existing_coverage_list": [...],
        "pending_insurance": str,
        "guide_question": str | None,
    }
    """
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"
    prompt = EXTRACT_COVERAGE_SLOTS_PROMPT.format(
        context=context_str,
        query=(query or "").strip(),
    )
    raw = llm_call(prompt, max_tokens=512)
    if not raw:
        return _fallback_result(is_complete=False)

    text = raw.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return _fallback_result(is_complete=False)

    if not isinstance(data, dict):
        return _fallback_result(is_complete=False)

    is_complete = bool(data.get("is_complete"))
    existing = data.get("existing_coverage_list")
    if not isinstance(existing, list):
        existing = []
    pending = (data.get("pending_insurance") or "").strip() or None
    guide = (data.get("guide_question") or "").strip() or None

    return {
        "is_complete": is_complete,
        "existing_coverage_list": existing,
        "pending_insurance": pending,
        "guide_question": guide if not is_complete else None,
    }


def _fallback_result(is_complete: bool) -> Dict[str, Any]:
    """LLM 不可用或解析失败时的兜底。"""
    return {
        "is_complete": is_complete,
        "existing_coverage_list": [],
        "pending_insurance": None,
        "guide_question": FALLBACK_GUIDE_QUESTION if not is_complete else None,
    }
