"""
医疗条款解析 - 上传、上下文、清除接口

- POST /api/clause/upload: 上传条款文件（PDF/Word/TXT）
- GET /api/clause/context: 获取当前会话条款上下文
- POST /api/clause/clear: 清除当前会话条款上下文
"""
import time
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.clause_context import (
    clear_clause_context,
    get_clause_context,
    save_clause_context,
)
from app.ragflow_dataset import (
    create_clause_dataset,
    parse_documents,
    upload_document,
    wait_for_parsing,
)
from config import settings
from core.auth import get_current_active_user
from models.user import User

router = APIRouter(prefix="/api/clause", tags=["医疗条款解析"])


def _allowed_ext() -> set:
    ext = getattr(settings, "CLAUSE_ALLOWED_EXT", "pdf,doc,docx,txt")
    return {x.strip().lower() for x in ext.split(",") if x.strip()}


def _max_size() -> int:
    return getattr(settings, "CLAUSE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024)


class ClearClauseBody(BaseModel):
    """清除条款上下文的请求体"""

    session_id: Optional[str] = None


@router.post("/upload")
async def clause_upload(
    file: UploadFile = File(...),
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """上传医疗条款文件（PDF/Word/TXT）。"""
    if not getattr(settings, "CLAUSE_PARSE_ENABLED", True):
        raise HTTPException(status_code=503, detail="条款解析功能暂未开放")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _allowed_ext():
        raise HTTPException(
            400, detail=f"不支持的文件格式，仅支持: {', '.join(_allowed_ext())}"
        )

    content = await file.read()
    if len(content) > _max_size():
        raise HTTPException(400, detail="文件大小超出限制")

    user_id = current_user.username
    sid = session_id or "default"

    ds_name = f"clause_{user_id}_{sid}_{int(time.time())}"
    create_res = create_clause_dataset(ds_name)
    if "error" in create_res:
        raise HTTPException(500, detail=create_res["error"])
    dataset_id = create_res.get("dataset_id")
    if not dataset_id:
        raise HTTPException(500, detail="创建知识库失败")

    upload_res = upload_document(dataset_id, content, file.filename or "upload.pdf")
    if "error" in upload_res:
        raise HTTPException(500, detail=upload_res["error"])

    doc_ids = upload_res.get("document_ids") or []
    if not doc_ids:
        raise HTTPException(500, detail="上传成功但未返回文档 ID")

    parse_documents(dataset_id, doc_ids)

    if not wait_for_parsing(dataset_id, doc_ids):
        raise HTTPException(504, detail="文件解析超时，请稍后重试或粘贴文本")

    save_clause_context(
        user_id,
        sid,
        "upload",
        dataset_id=dataset_id,
        file_name=file.filename,
    )

    return {
        "message": "条款已加载，可以开始提问",
        "dataset_id": dataset_id,
        "file_name": file.filename,
    }


@router.get("/context")
def clause_get_context(
    session_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    """获取当前会话的条款上下文。"""
    ctx = get_clause_context(current_user.username, session_id or "default")
    if not ctx:
        return {"loaded": False, "context": None}
    return {"loaded": True, "context": ctx}


@router.post("/clear")
def clause_clear(
    body: Optional[ClearClauseBody] = Body(None),
    current_user: User = Depends(get_current_active_user),
):
    """清除当前会话的条款上下文。"""
    sid = (body.session_id if body else None) or "default"
    clear_clause_context(current_user.username, sid)
    return {"message": "已清除条款上下文"}
