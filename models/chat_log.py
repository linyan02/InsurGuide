"""
交互日志与合规日志模型 - 用于审计与溯源

- InteractionLog：每轮对话会写一条，记录 user_id、问句、答案、引用片段数，便于统计与导出。
- ComplianceLog：当答案触发违规词并被屏蔽时写一条，记录问句、答案摘要、违规标记与备注。
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from core.database import Base


class InteractionLog(Base):
    """用户交互日志表：每轮问答写一条，用于行为分析与审计。"""
    __tablename__ = "interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    source_count = Column(Integer, default=0)  # 本回答引用了多少条知识库片段
    intent = Column(String(64), nullable=True)  # 意图标签，用于统计与看板
    session_id = Column(String(64), nullable=True)  # 会话 ID，用于恢复时绑定 clause_ctx
    clause_snapshot = Column(Text, nullable=True)  # P2-11：条款上下文 JSON 快照，恢复历史时用
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ComplianceLog(Base):
    """合规检测日志表：发生违规词屏蔽时写一条，便于排查与合规报告。"""
    __tablename__ = "compliance_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), index=True, nullable=False)
    query = Column(Text, nullable=True)
    answer_snapshot = Column(Text, nullable=True)  # 检测时的答案摘要（可截断到 2000 字）
    violated = Column(Boolean, default=False)
    remark = Column(String(255), nullable=True)  # 如 "违规表述屏蔽"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
