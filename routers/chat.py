"""
增强 RAG 多轮对话接口 - 产品文档核心接口

- POST /api/chat：一轮问答，传 user_id、query，可选 intent_mode、rewrite_mode，返回 answer、sources、意图等。
- POST /api/chat/stream：流式对话，返回 SSE，逐 chunk 推送答案。
- POST /api/chat/clear：清除该用户的对话上下文（Redis），相当于「重新开始」。
- GET /api/chat/history：当前用户最近若干条对话记录（标题列表），需登录。
- GET /api/chat/history/{log_id}：获取单条记录详情（问+答），用于点击「最近记录」展示并继续对话，需登录。
- POST /api/chat/context/restore：将当前用户上下文恢复为指定记录的那一轮，以便基于该对话继续问答，需登录。
"""
import json
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from core.auth import get_current_active_user
from core.database import get_db
from core.redis_store import clear_conversation_context, save_conversation_context
from models.chat_log import InteractionLog
from models.user import User
from services.rag.pipeline import run_chat_pipeline
from services.rag.pipeline_stream import run_chat_pipeline_stream
from services.rag.langchain_chain import run_chat_with_langchain

router = APIRouter(prefix="/api", tags=["增强RAG对话"])

# 侧栏「最近记录」展示条数
HISTORY_LIST_SIZE = 5
# 单条标题最大展示字数（超出截断）
HISTORY_TITLE_MAX_LEN = 24


class ChatRequest(BaseModel):
    """多轮对话请求体。user_id 用于区分用户、取/存对话上下文；intent_mode/rewrite_mode 为空则用全局配置；model_plan 为 pro/standard 选模型。"""
    user_id: str
    query: str
    intent_mode: Optional[str] = None   # rule | llm | llm_vector | bert，空则用配置
    rewrite_mode: Optional[str] = None  # rule | llm | llm_vector，空则用配置
    model_plan: Optional[str] = None    # pro=专业版(qwen-plus) | standard=标准版(qwen-turbo)，空则按 standard


class ChatResponse(BaseModel):
    """统一响应：code、message、data（内含 answer、source、intent 等）。"""
    code: int
    message: str
    data: Optional[dict] = None


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest = Body(..., description="用户唯一标识与提问"),
    db: Session = Depends(get_db),
):
    """
    多轮对话接口：接收 user_id、query，返回答案与溯源来源。
    流程：获取上下文 → RAGflow 检索 → 答案生成与合规校验 → 保存上下文与日志 → 返回结果。
    """
    user_id = (body.user_id or "").strip()
    query = (body.query or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")

    if settings.USE_LANGCHAIN_RAG:
        result = run_chat_with_langchain(
            db, user_id, query,
            intent_mode=body.intent_mode,
            rewrite_mode=body.rewrite_mode,
            model_plan=body.model_plan,
        )
    else:
        result = run_chat_pipeline(
            db, user_id, query,
            intent_mode=body.intent_mode,
            rewrite_mode=body.rewrite_mode,
            model_plan=body.model_plan,
        )
    if "error" in result:
        return ChatResponse(
            code=500,
            message=result["error"],
            data=None,
        )
    return ChatResponse(
        code=200,
        message="success",
        data={
            "answer": result["answer"],
            "context_count": result["context_count"],
            "source": result.get("sources") or [],
            "violated": result.get("violated", False),
            "state": result.get("state", "COMPLETE"),
            "intent": result.get("intent", "other"),
            "intent_cn": result.get("intent_cn", "其他"),
            "intent_confidence": result.get("intent_confidence", 0),
            "intent_method": result.get("intent_method", "rule"),
            "rewritten_query": result.get("rewritten_query", body.query),
            "rewrite_changed": result.get("rewrite_changed", False),
            "rewrite_method": result.get("rewrite_method", "none"),
            **({"intent_fallback_reason": result["intent_fallback_reason"]} if result.get("intent_fallback_reason") is not None else {}),
        },
    )


@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest = Body(..., description="用户唯一标识与提问"),
    db: Session = Depends(get_db),
):
    """
    流式对话接口：返回 SSE，答案逐 chunk 推送。仅使用标准 pipeline，不支持 LangChain 模式。
    """
    user_id = (body.user_id or "").strip()
    query = (body.query or "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id 不能为空")
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")

    async def event_generator():
        try:
            async for event in run_chat_pipeline_stream(
                db, user_id, query,
                intent_mode=body.intent_mode,
                rewrite_mode=body.rewrite_mode,
                model_plan=body.model_plan,
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/clear")
def clear_context(user_id: str = Body(..., embed=True)):
    """清除指定用户的对话上下文（Redis）"""
    ok = clear_conversation_context(user_id)
    return {"code": 200 if ok else 500, "message": "已清除上下文" if ok else "清除失败或 Redis 未就绪"}


class HistoryItem(BaseModel):
    """最近记录单条：id、标题（问句截断）、创建时间。"""
    id: int
    title: str
    created_at: Optional[str] = None


@router.get("/chat/history", response_model=dict)
def get_chat_history(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取当前登录用户最近若干条对话记录，用于侧栏「最近记录」展示。
    需在 Header 带 Authorization: Bearer <token>。按创建时间倒序，取最近 limit 条（默认 5）。
    """
    limit = min(max(1, limit), 20)
    rows = (
        db.query(InteractionLog)
        .filter(InteractionLog.user_id == current_user.username)
        .order_by(InteractionLog.created_at.desc())
        .limit(limit)
        .all()
    )
    items: List[HistoryItem] = []
    for r in rows:
        title = (r.query or "").strip()
        if len(title) > HISTORY_TITLE_MAX_LEN:
            title = title[:HISTORY_TITLE_MAX_LEN] + "…"
        created_at = r.created_at.isoformat() if r.created_at else None
        items.append(HistoryItem(id=r.id, title=title or "（无标题）", created_at=created_at))
    return {"code": 200, "message": "success", "data": [i.model_dump() for i in items]}


@router.get("/chat/history/{log_id}", response_model=dict)
def get_chat_history_item(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    获取单条对话记录详情（问句+回答），用于侧栏点击后展示并可基于该对话继续问答。
    仅能查询当前用户自己的记录。
    """
    row = (
        db.query(InteractionLog)
        .filter(InteractionLog.id == log_id, InteractionLog.user_id == current_user.username)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    created_at = row.created_at.isoformat() if row.created_at else None
    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": row.id,
            "query": row.query or "",
            "answer": row.answer or "",
            "created_at": created_at,
        },
    }


class RestoreContextRequest(BaseModel):
    """恢复上下文请求体：指定一条历史记录的 id，将该轮设为当前唯一上下文。"""
    log_id: int


@router.post("/chat/context/restore", response_model=dict)
def restore_context(
    body: RestoreContextRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    将当前用户的对话上下文恢复为指定历史记录的那一轮（仅保留该条问+答）。
    之后用户发送新消息时，将基于这一轮继续多轮对话。
    """
    row = (
        db.query(InteractionLog)
        .filter(InteractionLog.id == body.log_id, InteractionLog.user_id == current_user.username)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在或无权访问")
    clear_conversation_context(current_user.username)
    save_conversation_context(
        current_user.username,
        row.query or "",
        row.answer or "",
    )
    return {"code": 200, "message": "success", "data": None}
