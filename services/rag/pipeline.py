"""
增强 RAG 流水线编排：意图 → 改写 → 召回 → 融合 → 精排 → 答案与合规

本模块提供 run_chat_pipeline，与 app.chat_service.chat_once 行为一致，
当前召回只走 RAGflow；若将来接入多路召回（如 RAGflow + 本地向量库），
可在此处改为：recall → fusion → rerank → 再交给 answer_engine 生成答案。
"""
# 从 typing 模块导入类型注解，用于声明函数参数和返回值的类型，便于阅读和 IDE 提示
from typing import Any, Dict, List, Optional

# 从 SQLAlchemy 导入 Session：表示一次数据库会话，在本文件中用于写入交互日志和合规日志
from sqlalchemy.orm import Session

# 从 Redis 存储模块导入：获取用户历史对话、保存本轮对话，用于多轮上下文
from core.redis_store import (
    get_conversation_context,
    save_conversation_context,
)
# 导入日志表模型：InteractionLog 存每轮问答，ComplianceLog 存违规屏蔽记录
from models.chat_log import ComplianceLog, InteractionLog

# 意图、改写、RAGflow、答案生成、合规均复用 app 层实现，保证与 chat_once 一致
from app.intent import get_intent_label_cn, recognize as recognize_intent
from app.query_rewrite import rewrite as rewrite_query
from app.ragflow_client import call_ragflow
from app.answer_engine import generate_answer
from app.compliance import check_and_mask


def save_interaction_log(
    db: Session,
    user_id: str,
    query: str,
    answer: str,
    source_count: int = 0,
) -> None:
    """将本轮问答写入交互日志表。"""
    try:
        # 用传入的参数构造一条 InteractionLog 记录（对应 interaction_logs 表的一行）
        log = InteractionLog(
            user_id=user_id,
            query=query,
            answer=answer,
            source_count=source_count,
        )
        # 把这条记录加入当前会话的“待提交”列表
        db.add(log)
        # 真正执行 INSERT，把数据写入 MySQL
        db.commit()
    except Exception as e:
        # 发生任何异常时回滚本次会话的修改，避免脏数据
        if db:
            db.rollback()
        # 在控制台打印错误信息，便于排查
        print(f"写入交互日志失败: {e}")


def save_compliance_log(
    db: Session,
    user_id: str,
    query: Optional[str],
    answer_snapshot: Optional[str],
    violated: bool,
    remark: Optional[str] = None,
) -> None:
    """当发生违规词屏蔽时写入合规日志表。"""
    try:
        # 构造合规日志记录；answer_snapshot 超过 2000 字则截断，避免字段过长
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


def run_chat_pipeline(
    db: Session,
    user_id: str,
    query: str,
    *,
    intent_mode: Optional[str] = None,
    rewrite_mode: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行一轮增强 RAG 对话（与 chat_once 一致）：
    取上下文 → 意图识别 → 问题改写 → RAGflow 召回 → 生成答案 → 合规检测 → 存上下文与日志。
    返回结构含 answer、sources、intent、rewritten_query、violated 等。
    """
    # 从 Redis 取出该用户最近几轮对话，格式为 [{"query":"...", "answer":"..."}, ...]
    context = get_conversation_context(user_id)
    # 对用户当前问句做意图识别，mode 为空则用配置里的 INTENT_MODE（rule/llm/llm_vector/bert）
    intent_result = recognize_intent(query, mode=intent_mode)
    # 给意图加上中文展示名，便于前端或日志使用
    intent_result["intent_cn"] = get_intent_label_cn(intent_result.get("intent", "other"))
    # 结合 context 对 query 做改写（补全指代、省略），得到可独立检索的完整问句
    rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
    # 用改写后的问句去检索知识库，而不是用用户原句（避免“那理赔呢”这种短句检索差）
    search_query = rewrite_result["rewritten_query"]
    # 调用 RAGflow 接口，返回 { documents: [...], metadatas: [...] } 或 { error: "..." }
    ragflow_result = call_ragflow(search_query)
    # 若 RAGflow 返回了 error（如未配置、网络失败），则组装错误响应并直接返回，不再生成答案
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
        # 若意图用了 BERT 且发生了兜底（如超时），把原因带给前端便于排查
        if intent_result.get("fallback_reason") is not None:
            err_out["intent_fallback_reason"] = intent_result.get("fallback_reason")
        return err_out
    # 用检索到的知识库内容 + 历史 context 生成答案；这里先不做合规，下面统一做并记日志
    answer = generate_answer(query, ragflow_result, context, do_compliance=False)
    # 对答案做违规词检测，违规词会被替换为 [违规表述已屏蔽]；violated 表示是否发生过替换
    answer, violated = check_and_mask(answer)
    if violated:
        # 发生违规则写一条合规日志，方便后续审计
        save_compliance_log(db, user_id, query, answer, violated=True, remark="违规表述屏蔽")
    # 从 RAGflow 结果里取出每条片段的元数据（来源等）
    metadatas = ragflow_result.get("metadatas") or []
    # 把每条元数据里的“来源”抽出来，没有 source 则用 document_name，都没有则“未知”
    sources = [m.get("source", m.get("document_name", "未知")) for m in metadatas]
    # 把本轮“用户问 + 系统答”追加到 Redis 该用户的上下文中，供下一轮使用
    save_conversation_context(user_id, query, answer)
    # 把本轮问答写入 MySQL 交互日志表，source_count 为本轮引用的知识库片段数
    save_interaction_log(
        db, user_id, query, answer,
        source_count=len(ragflow_result.get("documents") or []),
    )
    # 组装成功时的返回结构，供路由层转成 API 响应
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
