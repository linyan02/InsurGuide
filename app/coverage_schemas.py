"""
保障重叠度 Slot Schema - 现有保障与待购险种的结构化定义

供 coverage_slots 与 coverage_overlap 使用，见产品方案 §3.5 险种矩阵。
"""
from typing import Any, Dict

INTENT_COVERAGE_OVERLAP = "coverage_overlap"

COVERAGE_OVERLAP_SCHEMA: Dict[str, Any] = {
    "description": "保障重叠度分析（多险种通用）",
    "required_fields": [
        "existing_coverage_list",
        "pending_insurance",
    ],
    "field_specs": {
        "existing_coverage_list": {
            "type": "list",
            "description": "用户现有保障列表，属性按险种类别选用",
            "item_spec": {
                "name": "险种名称（社保/百万医疗/重疾险/学平险/意外险/防癌险等）",
                "deductible": "免赔额（医疗险）",
                "has_outpatient": "是否含门诊（医疗险）",
                "coverage_scope": "保障范围简述（可选）",
                "death_benefit": "身故保额（意外/寿险类，可选）",
                "critical_illness_amount": "重疾保额（重疾险，可选）",
            },
        },
        "pending_insurance": {
            "type": "str",
            "description": "待购险种名称",
        },
    },
}
