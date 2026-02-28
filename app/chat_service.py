"""
增强 RAG 对话服务 - 编排上下文、意图识别、问题改写、RAGflow、答案生成、合规与日志

本模块是「一轮对话」的编排层：把意图识别、问题改写、知识库检索、答案生成、合规校验、
上下文保存和数据库日志串起来。API 层（如 chat 路由）只需调 chat_once 即可完成一整轮回答。
"""
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.answer_engine import generate_answer
from app.context_compressor import compress_context
from app.compliance import check_and_mask
from app.context_store import get_conversation_context, save_conversation_context
from app.intent import get_intent_label_cn, recognize as recognize_intent
from app.query_rewrite import rewrite as rewrite_query
from app.ragflow_client import call_ragflow
from models.chat_log import ComplianceLog, InteractionLog


def save_interaction_log(
    db: Session,
    user_id: str,
    query: str,
    answer: str,
    source_count: int = 0,
    intent: Optional[str] = None,
) -> None:
    """把本轮问答写入 MySQL 的交互日志表，用于统计与审计。"""
    try:
        log = InteractionLog(
            user_id=user_id,
            query=query,
            answer=answer,
            source_count=source_count,
            intent=intent,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        if db:
            db.rollback()
        print(f"写入交互日志失败: {e}")


def save_compliance_log(
    db: Session,
    user_id: str,
    query: Optional[str],
    answer_snapshot: Optional[str],
    violated: bool,
    remark: Optional[str] = None,
) -> None:
    """当答案触发违规词屏蔽时，把摘要写入合规日志表，便于后续排查。"""
    try:
        log = ComplianceLog(
            user_id=user_id,
            query=query,
            answer_snapshot=answer_snapshot[:2000] if answer_snapshot else None,
            violated=violated,
            remark=remark,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        if db:
            db.rollback()
        print(f"写入合规日志失败: {e}")


def chat_once(
    db: Session,
    user_id: str,
    query: str,
    *,
    intent_mode: Optional[str] = None,
    rewrite_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行一轮增强 RAG 对话：
    1. 获取历史上下文
    2. 意图识别（可选 intent_mode：rule | llm | llm_vector，默认读配置）
    3. 用户问题改写（可选 rewrite_mode：rule | llm | llm_vector）
    4. 用改写后问题调用 RAGflow 检索
    5. 生成答案并合规校验
    6. 保存上下文与日志
    返回 { "answer", "sources", "context_count", "violated", "intent", "rewritten_query", ... } 或 error
    """
    # 1. 从 Redis 取该用户最近几轮对话
    context = get_conversation_context(user_id)
    # 2. 意图识别（rule/llm/llm_vector/bert 等）
    intent_result = recognize_intent(query, mode=intent_mode)
    intent_result["intent_cn"] = get_intent_label_cn(intent_result.get("intent", "other"))
    # 3. 问题改写（补全指代、省略）
    rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
    search_query = rewrite_result["rewritten_query"]
    # 4. 用改写后的问题调 RAGflow 检索知识库
    ragflow_result = call_ragflow(search_query)
    if "error" in ragflow_result:
        err_out = {
            "error": ragflow_result["error"],
            "answer": None,
            "sources": [],
            "context_count": len(context),
            "violated": False,
            "intent": intent_result.get("intent", "other"),
            "intent_cn": intent_result.get("intent_cn"),
            "intent_confidence": intent_result.get("confidence", 0),
            "intent_method": intent_result.get("method", "rule"),
            "rewritten_query": rewrite_result.get("rewritten_query", query),
            "rewrite_changed": rewrite_result.get("changed", False),
            "rewrite_method": rewrite_result.get("method", "none"),
        }
        if intent_result.get("fallback_reason") is not None:
            err_out["intent_fallback_reason"] = intent_result.get("fallback_reason")
        return err_out
    # 5. 用检索结果 + 压缩后上下文生成答案
    compressed = compress_context(
        query,
        context,
        rewritten_query=rewrite_result.get("rewritten_query"),
    )
    answer = generate_answer(query, ragflow_result, compressed, do_compliance=False)
    answer, violated = check_and_mask(answer)
    if violated:
        save_compliance_log(
            db, user_id, query, answer, violated=True, remark="违规表述屏蔽"
        )
    metadatas = ragflow_result.get("metadatas") or []
    sources = [m.get("source", m.get("document_name", "未知")) for m in metadatas]
    # 6. 把本轮问答写入 Redis 上下文，并写交互日志
    save_conversation_context(user_id, query, answer)
    save_interaction_log(
        db, user_id, query, answer,
        source_count=len(ragflow_result.get("documents") or []),
        intent=intent_result.get("intent", "other"),
    )
    out = {
        "answer": answer,
        "sources": sources,
        "context_count": len(context) + 1,
        "violated": violated,
        "intent": intent_result.get("intent", "other"),
        "intent_cn": intent_result.get("intent_cn"),
        "intent_confidence": intent_result.get("confidence", 0),
        "intent_method": intent_result.get("method", "rule"),
        "rewritten_query": rewrite_result.get("rewritten_query", query),
        "rewrite_changed": rewrite_result.get("changed", False),
        "rewrite_method": rewrite_result.get("method", "none"),
    }
    if intent_result.get("fallback_reason") is not None:
        out["intent_fallback_reason"] = intent_result.get("fallback_reason")
    return out
