"""
流式增强 RAG 流水线：与 pipeline 逻辑一致，答案生成阶段以 SSE chunk 形式逐段输出。

流式接口 POST /api/chat/stream 使用本模块，不依赖 USE_LANGCHAIN_RAG。
"""
import asyncio
import json
import queue
import threading
from typing import Any, AsyncGenerator, Dict, Generator, Optional

from sqlalchemy.orm import Session

from core.redis_store import get_conversation_context, save_conversation_context

from config import settings
from app.intent import (
    INTENT_CLAUSE_PARSE,
    INTENT_COVERAGE_OVERLAP,
    INTENT_MEDICAL_INSURANCE,
    get_intent_label_cn,
    recognize as recognize_intent,
)
from app.llm_short import extract_insurance_slots
from app.coverage_slots import extract_coverage_slots
from app.coverage_overlap import compute_coverage_gap
from app.query_rewrite import rewrite as rewrite_query
from app.ragflow_client import (
    call_ragflow,
    enhance_query_for_intent,
    get_coverage_kb_ids,
)
from app.clause_context import get_clause_context
from app.answer_engine import (
    generate_answer_stream,
    enrich_answer_with_rich_content,
)
from app.context_compressor import compress_context
from app.compliance import check_and_mask
from app.model_plan import get_dashscope_model_for_plan

from services.rag.pipeline import (
    STATE_COMPLETE,
    STATE_GUIDING,
    save_interaction_log,
    save_compliance_log,
)


async def _stream_chunks_realtime(
    stream_gen: Generator[str, None, None],
    chunks_out: list,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    在子线程中消费同步生成器，每个 chunk 立刻放入队列；
    主协程从队列取出并 yield，实现真正的边生成边推送。
    chunks_out 由调用方传入，会在消费过程中被填充，供后续合规、日志使用。
    """
    chunk_queue: queue.Queue = queue.Queue()

    def producer():
        try:
            for c in stream_gen:
                chunk_queue.put(c)
                chunks_out.append(c)
        finally:
            chunk_queue.put(None)

    thread = threading.Thread(target=producer)
    thread.start()

    while True:
        chunk = await asyncio.to_thread(chunk_queue.get)
        if chunk is None:
            break
        yield {"type": "chunk", "content": chunk}


def _yield_done_event(out: Dict[str, Any]) -> Dict[str, Any]:
    """组装 done 事件结构，供前端消费。"""
    evt = {
        "type": "done",
        "answer": out.get("answer", ""),
        "source": out.get("sources", []),
        "intent_cn": out.get("intent_cn", ""),
        "context_count": out.get("context_count", 0),
        "violated": out.get("violated", False),
        "state": out.get("state", STATE_COMPLETE),
        "intent": out.get("intent", "other"),
        "intent_confidence": out.get("intent_confidence", 0),
        "rewritten_query": out.get("rewritten_query", ""),
    }
    if "clause_loaded" in out:
        evt["clause_loaded"] = out["clause_loaded"]
    return evt


async def run_chat_pipeline_stream(
    db: Session,
    user_id: str,
    query: str,
    *,
    intent_mode: Optional[str] = None,
    rewrite_mode: Optional[str] = None,
    model_plan: Optional[str] = None,
    session_id: Optional[str] = None,
    clause_text: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式版 Pipeline：与 run_chat_pipeline 逻辑一致，
    引导态直接 yield done；完整回答时 yield chunk 再 yield done。
    """
    context = get_conversation_context(user_id)
    intent_result = recognize_intent(query, mode=intent_mode)
    intent_result["intent_cn"] = get_intent_label_cn(intent_result.get("intent", "other"))
    intent_name = intent_result.get("intent", "other")

    # ---------- 百万医疗险引导态 ----------
    if intent_name == INTENT_MEDICAL_INSURANCE:
        slots_result = extract_insurance_slots(query, context)
        if not slots_result.get("is_complete", False):
            guide_question = slots_result.get("guide_question") or (
                "百万医疗险对年龄和健康状况要求较高。请问被保人多大年纪？"
                "是否有医保？过去两年是否有过住院记录或慢性病、结节等情况？"
            )
            save_conversation_context(user_id, query, guide_question)
            yield _yield_done_event({
                "answer": guide_question,
                "sources": [],
                "context_count": len(context) + 1,
                "violated": False,
                "state": STATE_GUIDING,
                "intent": intent_name,
                "intent_cn": intent_result.get("intent_cn"),
                "intent_confidence": intent_result.get("confidence", 0),
                "rewritten_query": query,
            })
            return
        search_query = slots_result.get("search_optimization_query") or query
        rewrite_result = {"rewritten_query": search_query, "changed": True, "method": "extract_slots"}

    # ---------- 保障重叠度引导态 ----------
    elif intent_name == INTENT_COVERAGE_OVERLAP and getattr(
        settings, "COVERAGE_OVERLAP_ENABLED", True
    ):
        slots_result = extract_coverage_slots(query, context)
        if not slots_result.get("is_complete", False):
            guide_question = slots_result.get("guide_question") or "请补充您的保障情况以便分析。"
            save_conversation_context(user_id, query, guide_question)
            yield _yield_done_event({
                "answer": guide_question,
                "sources": [],
                "context_count": len(context) + 1,
                "violated": False,
                "state": STATE_GUIDING,
                "intent": intent_name,
                "intent_cn": intent_result.get("intent_cn"),
                "intent_confidence": intent_result.get("confidence", 0),
                "rewritten_query": query,
            })
            return
        rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
        search_query = enhance_query_for_intent(
            rewrite_result["rewritten_query"], INTENT_COVERAGE_OVERLAP
        )
        kb_ids = get_coverage_kb_ids()
        top_k = getattr(settings, "COVERAGE_OVERLAP_TOP_K", 5)
        use_keyword = getattr(settings, "COVERAGE_OVERLAP_KEYWORD", True)
        ragflow_result = call_ragflow(
            search_query,
            knowledge_base_id=kb_ids if kb_ids else None,
            top_k=top_k,
            keyword=use_keyword,
        )
        if "error" in ragflow_result:
            yield {"type": "error", "message": ragflow_result["error"]}
            return
        analysis_result = compute_coverage_gap(
            slots_result,
            ragflow_result.get("documents") or [],
        )
        compressed = compress_context(
            query,
            context,
            rewritten_query=rewrite_result.get("rewritten_query"),
        )
        dashscope_model = get_dashscope_model_for_plan(model_plan)
        stream_gen = generate_answer_stream(
            query,
            ragflow_result,
            compressed,
            model=dashscope_model,
            intent_name=INTENT_COVERAGE_OVERLAP,
            coverage_slots=slots_result,
            analysis_result=analysis_result,
        )
        chunks_list: list = []
        async for event in _stream_chunks_realtime(stream_gen, chunks_list):
            yield event

        answer = "".join(chunks_list)
        answer = enrich_answer_with_rich_content(answer, ragflow_result)
        answer, violated = check_and_mask(answer)
        if violated:
            save_compliance_log(db, user_id, query, answer, violated=True, remark="违规表述屏蔽")
        metadatas = ragflow_result.get("metadatas") or []
        sources = [m.get("source", m.get("document_name", "未知")) for m in metadatas]
        save_conversation_context(user_id, query, answer)
        save_interaction_log(
            db, user_id, query, answer,
            source_count=len(ragflow_result.get("documents") or []),
            intent=intent_name,
            session_id=session_id,
        )
        out = _yield_done_event({
            "answer": answer,
            "sources": sources,
            "context_count": len(context) + 1,
            "violated": violated,
            "state": STATE_COMPLETE,
            "intent": intent_name,
            "intent_cn": intent_result.get("intent_cn"),
            "intent_confidence": intent_result.get("confidence", 0),
            "rewritten_query": rewrite_result.get("rewritten_query", query),
        })
        yield out
        return

    # ---------- 医疗条款解析 ----------
    elif intent_name == INTENT_CLAUSE_PARSE and getattr(
        settings, "CLAUSE_PARSE_ENABLED", True
    ):
        from app.clause_context import save_clause_context as _save_clause

        clause_ctx = get_clause_context(user_id, session_id or "default")
        effective_clause_text = clause_text or ""
        if clause_text and len(clause_text.strip()) > 100:
            _save_clause(
                user_id, session_id or "default", "text",
                text_preview=clause_text[:500], text_full=clause_text,
            )
            clause_ctx = get_clause_context(user_id, session_id or "default")
        elif clause_ctx and clause_ctx.get("source") == "text":
            effective_clause_text = clause_ctx.get("text_full") or ""
        if not clause_ctx and not effective_clause_text.strip():
            guide_q = "要准确解读条款，请先粘贴相关条款内容，或上传条款文件（PDF/Word/TXT）。"
            save_conversation_context(user_id, query, guide_q)
            yield _yield_done_event({
                "answer": guide_q,
                "sources": [],
                "context_count": len(context) + 1,
                "violated": False,
                "state": STATE_GUIDING,
                "intent": intent_name,
                "intent_cn": intent_result.get("intent_cn"),
                "intent_confidence": intent_result.get("confidence", 0),
                "rewritten_query": query,
                "clause_loaded": False,
            })
            return
        rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
        search_query = rewrite_result["rewritten_query"]
        default_kb = getattr(settings, "RAGFLOW_KNOWLEDGE_BASE_ID", None)
        kb_ids: list = []
        if clause_ctx and clause_ctx.get("dataset_id"):
            kb_ids.append(clause_ctx["dataset_id"])
        if default_kb and default_kb not in kb_ids:
            kb_ids.append(default_kb)
        if not kb_ids:
            kb_ids = [default_kb] if default_kb else None
        ragflow_result = call_ragflow(
            search_query,
            knowledge_base_id=kb_ids if kb_ids else None,
            top_k=getattr(settings, "RAGFLOW_TOP_K", 3),
        )
        if "error" in ragflow_result:
            yield {"type": "error", "message": ragflow_result["error"]}
            return
        compressed = compress_context(
            query,
            context,
            rewritten_query=rewrite_result.get("rewritten_query"),
        )
        dashscope_model = get_dashscope_model_for_plan(model_plan)
        stream_gen = generate_answer_stream(
            query,
            ragflow_result,
            compressed,
            model=dashscope_model,
            intent_name=INTENT_CLAUSE_PARSE,
            clause_text=effective_clause_text.strip() or None,
            clause_context=clause_ctx,
        )
        chunks_list: list = []
        async for event in _stream_chunks_realtime(stream_gen, chunks_list):
            yield event

        answer = "".join(chunks_list)
        if len(context) <= 1 and effective_clause_text and len(effective_clause_text.strip()) > 50:
            from app.answer_engine import extract_clause_structured, _format_clause_structured_table
            extracted = extract_clause_structured(
                effective_clause_text.strip(), model=dashscope_model
            )
            if extracted:
                answer = answer.rstrip() + _format_clause_structured_table(extracted)
        answer = enrich_answer_with_rich_content(answer, ragflow_result)
        answer, violated = check_and_mask(answer)
        if violated:
            save_compliance_log(db, user_id, query, answer, violated=True, remark="违规表述屏蔽")
        metadatas = ragflow_result.get("metadatas") or []
        sources = [m.get("source", m.get("document_name", "未知")) for m in metadatas]
        save_conversation_context(user_id, query, answer)
        snap = None
        if clause_ctx:
            try:
                snap_copy = dict(clause_ctx)
                if snap_copy.get("text_full") and len(str(snap_copy["text_full"])) > 16384:
                    snap_copy["text_full"] = str(snap_copy["text_full"])[:16384] + "…"
                snap = json.dumps(snap_copy, ensure_ascii=False)
            except (TypeError, ValueError):
                snap = None
        save_interaction_log(
            db, user_id, query, answer,
            source_count=len(ragflow_result.get("documents") or []),
            intent=intent_name,
            session_id=session_id or "default",
            clause_snapshot=snap,
        )
        out = _yield_done_event({
            "answer": answer,
            "sources": sources,
            "context_count": len(context) + 1,
            "violated": violated,
            "state": STATE_COMPLETE,
            "intent": intent_name,
            "intent_cn": intent_result.get("intent_cn"),
            "intent_confidence": intent_result.get("confidence", 0),
            "rewritten_query": rewrite_result.get("rewritten_query", query),
            "clause_loaded": bool(clause_ctx),
        })
        yield out
        return

    # ---------- 默认路径 ----------
    rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
    search_query = rewrite_result["rewritten_query"]
    ragflow_result = call_ragflow(search_query)

    if "error" in ragflow_result:
        yield {"type": "error", "message": ragflow_result["error"]}
        return

    compressed = compress_context(
        query,
        context,
        rewritten_query=rewrite_result.get("rewritten_query"),
    )
    dashscope_model = get_dashscope_model_for_plan(model_plan)
    stream_gen = generate_answer_stream(
        query, ragflow_result, compressed, model=dashscope_model
    )
    chunks_list: list = []
    async for event in _stream_chunks_realtime(stream_gen, chunks_list):
        yield event

    answer = "".join(chunks_list)
    answer = enrich_answer_with_rich_content(answer, ragflow_result)
    answer, violated = check_and_mask(answer)
    if violated:
        save_compliance_log(db, user_id, query, answer, violated=True, remark="违规表述屏蔽")
    metadatas = ragflow_result.get("metadatas") or []
    sources = [m.get("source", m.get("document_name", "未知")) for m in metadatas]
    save_conversation_context(user_id, query, answer)
    save_interaction_log(
        db, user_id, query, answer,
        source_count=len(ragflow_result.get("documents") or []),
        intent=intent_result.get("intent", "other"),
        session_id=session_id,
    )
    out = _yield_done_event({
        "answer": answer,
        "sources": sources,
        "context_count": len(context) + 1,
        "violated": violated,
        "state": STATE_COMPLETE,
        "intent": intent_result.get("intent", "other"),
        "intent_cn": intent_result.get("intent_cn"),
        "intent_confidence": intent_result.get("confidence", 0),
        "rewritten_query": rewrite_result.get("rewritten_query", query),
    })
    if intent_result.get("fallback_reason") is not None:
        out["intent_fallback_reason"] = intent_result["fallback_reason"]
    yield out
