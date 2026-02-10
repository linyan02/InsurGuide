"""
LangChain 增强 RAG 编排链：意图 → 改写 → 检索（RAGflow + 可选 Chroma）→ DashScopeLLM 生成 → 合规 → 日志

与 run_chat_pipeline 返回结构一致，便于 API 层通过 USE_LANGCHAIN_RAG 切换。
"""
import json
from typing import Any, Dict, List, Optional

from langchain.chains import LLMChain
from langchain_core.documents import Document
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session

from config import settings
from core.redis_store import get_conversation_context, save_conversation_context
from app.intent import get_intent_label_cn, recognize as recognize_intent
from app.query_rewrite import rewrite as rewrite_query
from app.compliance import check_and_mask
from services.rag.langchain_ragflow_retriever import RAGflowRetriever
from services.rag.langchain_dashscope_llm import DashScopeLLM
from services.rag.pipeline import save_interaction_log, save_compliance_log


# 与 app.answer_engine 保持一致，供 LangChain Prompt 使用
INSURANCE_PROMPT_TEMPLATE = """
基于以下知识库内容，结合用户历史对话上下文，回答用户问题，要求：
1. 语言简洁，符合保险行业规范，避免专业术语过度堆砌；
2. 必须引用知识库内容，禁止编造信息；
3. 结尾添加合规声明：本内容仅供参考，不构成投保建议，具体以保险合同条款为准。

知识库内容：
{knowledge_content}

历史上下文：
{context}

用户问题：
{query}
"""


def _build_knowledge_content_from_docs(docs: List[Document]) -> str:
    """从 LangChain Document 列表拼成带来源的知识库文本。"""
    parts = []
    for d in docs:
        meta = d.metadata or {}
        source = meta.get("source", meta.get("document_name", "未知"))
        parts.append(f"【来源：{source}】\n{d.page_content}")
    return "\n\n".join(parts) if parts else "暂无相关知识库内容"


def run_chat_with_langchain(
    db: Session,
    user_id: str,
    query: str,
    *,
    intent_mode: Optional[str] = None,
    rewrite_mode: Optional[str] = None,
    use_chroma_recall: bool = False,
    chroma_collection_name: Optional[str] = None,
    chroma_k: int = 3,
) -> Dict[str, Any]:
    """
    使用 LangChain 执行一轮增强 RAG 对话：
    取上下文 → 意图识别 → 问题改写 → RAGflow（+ 可选 Chroma）检索 → DashScopeLLM 生成 → 合规 → 存上下文与日志。
    返回与 run_chat_pipeline 相同的结构，便于 /api/chat 统一处理。
    """
    context = get_conversation_context(user_id)
    intent_result = recognize_intent(query, mode=intent_mode)
    intent_result["intent_cn"] = get_intent_label_cn(intent_result.get("intent", "other"))
    rewrite_result = rewrite_query(query, context, mode=rewrite_mode)
    search_query = rewrite_result["rewritten_query"]

    # 主路：RAGflow Retriever
    top_k = getattr(settings, "RAGFLOW_TOP_K", 5)
    ragflow_retriever = RAGflowRetriever(top_k=top_k)
    docs = ragflow_retriever.get_relevant_documents(search_query)

    # 可选：叠加 Chroma 召回并合并去重（简单按 content 去重）
    if use_chroma_recall and chroma_collection_name:
        try:
            from services.rag.langchain_chroma import get_chroma_retriever
            chroma_retriever = get_chroma_retriever(
                collection_name=chroma_collection_name,
                k=chroma_k,
            )
            chroma_docs = chroma_retriever.get_relevant_documents(search_query)
            seen = {d.page_content.strip() for d in docs}
            for d in chroma_docs:
                c = (d.page_content or "").strip()
                if c and c not in seen:
                    seen.add(c)
                    docs.append(d)
        except Exception:
            pass

    # 检索结果为空（如 RAGflow 未配置或知识库无命中）时返回错误结构
    if not docs:
        err_out = {
            "error": "检索无结果（请检查 RAGflow 配置或知识库）",
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

    knowledge_content = _build_knowledge_content_from_docs(docs)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"

    prompt = PromptTemplate(
        input_variables=["knowledge_content", "context", "query"],
        template=INSURANCE_PROMPT_TEMPLATE,
    )
    llm = DashScopeLLM()
    chain = LLMChain(llm=llm, prompt=prompt)
    answer = chain.run(
        knowledge_content=knowledge_content,
        context=context_str,
        query=query,
    )
    if isinstance(answer, str):
        answer = answer.strip()
    else:
        answer = (answer or "").strip()

    answer, violated = check_and_mask(answer)
    if violated:
        save_compliance_log(db, user_id, query, answer, violated=True, remark="违规表述屏蔽")

    sources = [
        (d.metadata or {}).get("source", (d.metadata or {}).get("document_name", "未知"))
        for d in docs
    ]
    save_conversation_context(user_id, query, answer)
    save_interaction_log(db, user_id, query, answer, source_count=len(docs))

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
