"""
保险产品要素矩阵 - 百万医疗险等意图的核心要素定义

用于需求分析拦截：在意图识别后，根据要素完整度决定是否执行 RAG 检索，
或发起专业追问引导用户补全关键信息。
"""
from typing import Any, Dict, List, Optional

# 意图：百万医疗险
INTENT_MEDICAL_INSURANCE = "medical_insurance"

# 百万医疗险 6 大核心要素（与产品需求文档一致）
INSURANCE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    INTENT_MEDICAL_INSURANCE: {
        "description": "百万医疗险咨询",
        "required_fields": [
            "age",           # 被保人年龄 (int)，影响费率与承保条件
            "has_social_security",  # 是否有医保 (bool)
            "health_condition",     # 健康状况 (str)，含子项检查
        ],
        "optional_fields": [
            "special_needs",  # 特殊需求（如异地就医、特需病房等）
        ],
        "field_specs": {
            "age": {
                "type": "int",
                "description": "被保人年龄，单位：岁",
                "range": [0, 120],
            },
            "has_social_security": {
                "type": "bool",
                "description": "是否有城镇职工/城乡居民医保",
            },
            "health_condition": {
                "type": "dict",
                "description": "健康状况子项",
                "sub_fields": {
                    "hospitalization_history": "过去两年是否有住院记录 (bool)",
                    "nodule": "是否有器官结节（甲状腺、肺等）(bool)",
                    "chronic_disease": "是否有慢性病（高血压、糖尿病等）(bool)",
                },
            },
            "special_needs": {
                "type": "str",
                "description": "特殊需求描述，如异地就医、特需病房等",
            },
        },
    },
}


def extract_health_sub_fields(data: Dict[str, Any]) -> Dict[str, Optional[bool]]:
    """
    从 health_condition 中提取子项。
    health_condition 可以是：
    - 字符串描述，如 "身体较好"、"有高血压"
    - 字典，如 {"hospitalization_history": false, "nodule": false, "chronic_disease": false}
    """
    hc = data.get("health_condition")
    result = {
        "hospitalization_history": None,
        "nodule": None,
        "chronic_disease": None,
    }
    if hc is None:
        return result
    if isinstance(hc, dict):
        result["hospitalization_history"] = hc.get("hospitalization_history")
        result["nodule"] = hc.get("nodule")
        result["chronic_disease"] = hc.get("chronic_disease")
    return result


def validate_schema_completeness(
    intent: str,
    extracted: Dict[str, Any],
) -> Dict[str, Any]:
    """
    对比提取结果与 Schema 的完整度。
    返回 {"is_complete": bool, "missing_fields": [...], "extracted": {...}}
    """
    schema = INSURANCE_SCHEMAS.get(intent)
    if not schema:
        return {
            "is_complete": True,  # 未知意图不拦截
            "missing_fields": [],
            "extracted": extracted,
        }

    required = schema.get("required_fields", [])
    missing: List[str] = []

    for field in required:
        val = extracted.get(field)
        if val is None or val == "":
            missing.append(field)
            continue
        spec = schema.get("field_specs", {}).get(field)
        if not spec:
            continue
        if spec.get("type") == "dict" and isinstance(val, dict):
            sub_spec = spec.get("sub_fields", {})
            sub_keys = list(sub_spec.keys()) if isinstance(sub_spec, dict) else []
            for k in sub_keys:
                if val.get(k) is None and k not in ("special_needs",):
                    missing.append(f"{field}.{k}")
                    break

    return {
        "is_complete": len(missing) == 0,
        "missing_fields": missing,
        "extracted": extracted,
    }


def normalize_extracted_for_validation(extracted: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 LLM 返回的提取结果规范化，便于与 Schema 比对。
    如 age 可能是字符串 "45"，需转为 int。
    """
    out = dict(extracted)
    if "age" in out and out["age"] is not None:
        try:
            v = out["age"]
            if isinstance(v, str) and v.strip().replace("-", "").isdigit():
                out["age"] = int(v.strip().replace("-", "").split()[0])
            elif isinstance(v, (int, float)):
                out["age"] = int(v)
        except (ValueError, TypeError):
            pass
    if "has_social_security" in out and out["has_social_security"] is not None:
        v = out["has_social_security"]
        if isinstance(v, str):
            out["has_social_security"] = v.lower() in ("是", "有", "yes", "true", "1")
        else:
            out["has_social_security"] = bool(v)
    return out
