"""
保障重叠度计算 - 基于 Slot 与 RAG 检索结果，计算保障区间重叠

一期：规则实现，产出 overlap_matrix、marginal_contribution、recommendation 供 LLM 生成最终答案。
"""
from typing import Any, Dict, List


def compute_coverage_gap(
    slots: Dict[str, Any],
    rag_docs: List[str],
) -> Dict[str, Any]:
    """
    计算保障重叠情况（简化规则版）。
    返回：
    {
        "overlap_matrix": [...],
        "marginal_contribution": "高/中/低",
        "recommendation": "买/不买/换",
    }
    """
    existing = slots.get("existing_coverage_list") or []
    pending = (slots.get("pending_insurance") or "").strip() or "待购险种"

    # 标准化现有保障名
    existing_names = {_normalize_name(c.get("name") or "") for c in existing if c.get("name")}
    has_social = "社保" in existing_names or "医保" in existing_names
    has_supplement = "商业补充医疗" in existing_names or "补充医疗" in existing_names
    has_million = "百万医疗" in existing_names
    has_accident = "意外险" in existing_names

    # 获取补充医疗关键属性
    supplement_deductible = None
    supplement_outpatient = None
    for c in existing:
        name = _normalize_name(c.get("name") or "")
        if name in ("商业补充医疗", "补充医疗"):
            d = c.get("deductible")
            if d is not None:
                try:
                    supplement_deductible = 0 if d in (0, "0", "0免赔") else int(float(str(d)))
                except (ValueError, TypeError):
                    pass
            o = c.get("has_outpatient")
            if o is not None:
                supplement_outpatient = o in (True, "true", "是", "有", "含")
            break

    overlap_matrix: List[Dict[str, str]] = []
    pending_lower = pending.lower() if isinstance(pending, str) else ""

    # 学平险场景
    if "学平险" in pending or "学平" in pending_lower:
        # 小病/门诊
        if has_supplement and supplement_deductible == 0 and supplement_outpatient:
            overlap_matrix.append({
                "scene": "小病/门诊（感冒发烧、磕碰等）",
                "existing": "商业补充医疗（0免赔含门诊）已覆盖",
                "pending": "学平险也有门诊责任",
                "overlap": "重叠",
            })
        elif has_supplement:
            overlap_matrix.append({
                "scene": "小病/门诊",
                "existing": "商业补充医疗（待确认免赔额与门诊）",
                "pending": "学平险有门诊责任",
                "overlap": "待确认",
            })
        else:
            overlap_matrix.append({
                "scene": "小病/门诊",
                "existing": "未明确" if not has_supplement else "有补充医疗",
                "pending": "学平险有门诊责任",
                "overlap": "无重叠",
            })

        # 大病住院
        if has_million:
            overlap_matrix.append({
                "scene": "大病住院（>1万）",
                "existing": "百万医疗已覆盖",
                "pending": "学平险住院额度较低",
                "overlap": "重叠",
            })
        else:
            overlap_matrix.append({
                "scene": "大病住院",
                "existing": "无百万医疗" if not has_million else "有",
                "pending": "学平险有住院责任",
                "overlap": "部分重叠",
            })

        # 身故/伤残
        overlap_matrix.append({
            "scene": "意外身故/伤残",
            "existing": "医疗险通常不赔" + ("；意外险可赔" if has_accident else ""),
            "pending": "学平险有身故/伤残赔付",
            "overlap": "无重叠" if not has_accident else "部分重叠",
        })

    else:
        # 通用兜底
        overlap_matrix.append({
            "scene": "保障范围",
            "existing": ", ".join(existing_names) if existing_names else "未提供",
            "pending": str(pending),
            "overlap": "需结合知识库分析",
        })

    # 计算边际贡献与建议
    overlap_count = sum(1 for r in overlap_matrix if r.get("overlap") == "重叠")
    total = len(overlap_matrix)
    if total > 0:
        overlap_ratio = overlap_count / total
        if overlap_ratio >= 0.7:
            marginal = "低"
            recommendation = "不买"
            if "学平险" in pending and not has_accident:
                recommendation = "换购意外险（身故保额更高、保费更低）"
        elif overlap_ratio >= 0.4:
            marginal = "中"
            recommendation = "视情况而定，建议对比条款"
        else:
            marginal = "高"
            recommendation = "可买"
    else:
        marginal = "中"
        recommendation = "需结合知识库进一步分析"

    return {
        "overlap_matrix": overlap_matrix,
        "marginal_contribution": marginal,
        "recommendation": recommendation,
    }


def _normalize_name(name: str) -> str:
    """标准化险种名称。"""
    if not name:
        return ""
    n = str(name).strip()
    if "社保" in n or "医保" in n:
        return "社保"
    if "补充" in n and "医疗" in n:
        return "商业补充医疗"
    if "百万" in n or "医疗" in n:
        return "百万医疗"
    if "学平" in n:
        return "学平险"
    if "意外" in n:
        return "意外险"
    return n
