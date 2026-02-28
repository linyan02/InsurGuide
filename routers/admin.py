"""
管理端看板 - P1-7

GET /api/admin/dashboard：近 N 天核心指标（交互总量、合规拦截、条款解析次数、活跃用户、意图分布）
需登录（可选：后续增加 is_superuser 校验）
"""
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.auth import get_current_active_user
from core.database import get_db
from models.chat_log import InteractionLog, ComplianceLog
from models.user import User
from app.intent import get_intent_label_cn

router = APIRouter(prefix="/api/admin", tags=["管理看板"])


@router.get("/dashboard")
def get_dashboard(
    days: int = Query(7, ge=1, le=90, description="统计近 N 天"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    管理端看板：近 N 天核心指标。
    需在 Header 带 Authorization: Bearer <token>。
    """
    tz = timezone.utc
    since = datetime.now(tz=tz) - timedelta(days=days)

    # 交互总量：近 N 天 interaction_logs 条数
    total_interactions = (
        db.query(func.count(InteractionLog.id))
        .filter(InteractionLog.created_at >= since)
        .scalar()
        or 0
    )

    # 合规拦截：compliance_logs 中 violated=true
    compliance_violations = (
        db.query(func.count(ComplianceLog.id))
        .filter(
            ComplianceLog.violated == True,
            ComplianceLog.created_at >= since,
        )
        .scalar()
        or 0
    )

    # 条款解析次数：intent='clause_parse'
    clause_parse_count = (
        db.query(func.count(InteractionLog.id))
        .filter(
            InteractionLog.intent == "clause_parse",
            InteractionLog.created_at >= since,
        )
        .scalar()
        or 0
    )

    # 活跃用户数：user_id 去重
    active_users = (
        db.query(func.count(func.distinct(InteractionLog.user_id)))
        .filter(InteractionLog.created_at >= since)
        .scalar()
        or 0
    )

    # 意图分布：按 intent 分组统计
    intent_rows = (
        db.query(InteractionLog.intent, func.count(InteractionLog.id).label("count"))
        .filter(
            InteractionLog.created_at >= since,
            InteractionLog.intent.isnot(None),
            InteractionLog.intent != "",
        )
        .group_by(InteractionLog.intent)
        .all()
    )
    intent_distribution: List[dict] = []
    for intent_val, cnt in intent_rows:
        intent_val = intent_val or "other"
        intent_distribution.append({
            "intent": intent_val,
            "intent_cn": get_intent_label_cn(intent_val),
            "count": cnt,
        })

    return {
        "code": 200,
        "message": "success",
        "data": {
            "days": days,
            "total_interactions": total_interactions,
            "compliance_violations": compliance_violations,
            "clause_parse_count": clause_parse_count,
            "active_users": active_users,
            "intent_distribution": intent_distribution,
        },
    }
