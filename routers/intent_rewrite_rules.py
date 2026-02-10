"""
意图规则与改写规则 - 向量库写入接口
供 llm_vector 模式使用：将意图规则、改写示例写入对应集合，便于按业务热更新
"""
from typing import List, Optional
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from core.vector_db import vector_db
from config import settings

router = APIRouter(prefix="/api", tags=["意图与改写规则"])


class IntentRuleAdd(BaseModel):
    """单条意图规则：文档内容会用于向量检索，供 LLM 参考"""
    content: str  # 例如："意图：claims。关键词：理赔、赔付、报销。说明：用户问理赔条件、流程、材料时归为此类。"
    rule_id: Optional[str] = None  # 可选，不传则自动生成


class RewriteRuleAdd(BaseModel):
    """单条改写示例：原问+上下文+改写结果，供 LLM few-shot"""
    content: str  # 例如："原问：那理赔呢。上下文：重疾险等待期。改写：重疾险理赔条件与流程。"
    rule_id: Optional[str] = None


@router.post("/intent-rules/add")
def add_intent_rules(body: List[IntentRuleAdd] = Body(...)):
    """批量写入意图规则到向量库的 intent_rules 集合，意图模式为 llm_vector 时会检索这些规则供 LLM 参考。"""
    if not body:
        raise HTTPException(status_code=400, detail="请至少提供一条规则")
    if vector_db.client is None:
        raise HTTPException(status_code=503, detail="向量数据库未就绪")
    coll_name = getattr(settings, "INTENT_RULES_COLLECTION", "intent_rules")
    docs = [r.content for r in body]
    ids = [r.rule_id or f"intent_{i}" for i, r in enumerate(body)]
    ok = vector_db.add_to_collection(coll_name, docs, ids=ids)
    if not ok:
        raise HTTPException(status_code=500, detail="写入意图规则失败")
    return {"code": 200, "message": "ok", "count": len(body)}


@router.post("/rewrite-rules/add")
def add_rewrite_rules(body: List[RewriteRuleAdd] = Body(...)):
    """批量写入改写示例到向量库的 rewrite_rules 集合，改写模式为 llm_vector 时会检索这些示例供 LLM 参考。"""
    if not body:
        raise HTTPException(status_code=400, detail="请至少提供一条示例")
    if vector_db.client is None:
        raise HTTPException(status_code=503, detail="向量数据库未就绪")
    coll_name = getattr(settings, "REWRITE_RULES_COLLECTION", "rewrite_rules")
    docs = [r.content for r in body]
    ids = [r.rule_id or f"rewrite_{i}" for i, r in enumerate(body)]
    ok = vector_db.add_to_collection(coll_name, docs, ids=ids)
    if not ok:
        raise HTTPException(status_code=500, detail="写入改写示例失败")
    return {"code": 200, "message": "ok", "count": len(body)}
