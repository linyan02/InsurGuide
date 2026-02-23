"""
答案生成与优化 - 基于 RAGflow 检索结果 + 保险领域 Prompt 模板 + 轻量 LLM
产品文档：结合知识库内容与历史上下文，生成答案后进行合规校验
"""
import json
from typing import Any, Dict, List, Optional

from app.compliance import check_and_mask
from config import settings


# 保险领域 Prompt 模板（与产品技术文档一致）
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


def build_knowledge_content(ragflow_result: Dict[str, Any]) -> str:
    """从 RAGflow 返回结果整理成一段带来源的文本，供 Prompt 里的「知识库内容」使用。"""
    documents = ragflow_result.get("documents") or []
    metadatas = ragflow_result.get("metadatas") or []
    parts = []
    for i, doc in enumerate(documents):
        meta = metadatas[i] if i < len(metadatas) else {}
        source = meta.get("source", meta.get("document_name", "未知"))
        parts.append(f"【来源：{source}】\n{doc}")
    return "\n\n".join(parts) if parts else "暂无相关知识库内容"


def generate_answer(
    query: str,
    ragflow_result: Dict[str, Any],
    context: List[Dict[str, Any]],
    *,
    do_compliance: bool = True,
    model: Optional[str] = None,
) -> str:
    """
    结合 RAGflow 检索结果与历史上下文生成答案。do_compliance=True 时会调用合规检测并替换违规词。
    model：DashScope 模型名，如 qwen-turbo、qwen-plus，空则用默认。
    """
    knowledge_content = build_knowledge_content(ragflow_result)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"
    prompt = INSURANCE_PROMPT_TEMPLATE.format(
        knowledge_content=knowledge_content,
        context=context_str,
        query=query,
    )
    answer = call_light_llm(prompt, model=model)
    if do_compliance:
        answer, _ = check_and_mask(answer)
    return answer


def call_light_llm(prompt: str, model: Optional[str] = None) -> str:
    """
    调用轻量 LLM 生成回复。
    优先使用 API 模式（通义千问/OpenAI），无 GPU 时推荐；可选本地 Qwen。
    model：API 模式下使用的 DashScope/OpenAI 模型名，空则用默认。
    """
    mode = (settings.LLM_MODE or "api").lower()
    if mode == "local":
        return _call_local_llm(prompt)
    return _call_api_llm(prompt, model=model)


def _call_api_llm(prompt: str, model: Optional[str] = None) -> str:
    """通义千问或 OpenAI 等 API。model 仅对 DashScope 生效，空则用 qwen-turbo。"""
    if settings.DASHSCOPE_API_KEY:
        return _call_dashscope(prompt, model=model)
    if settings.OPENAI_API_KEY:
        return _call_openai(prompt)
    return _fallback_answer(prompt)


def _call_dashscope(prompt: str, model: Optional[str] = None) -> str:
    """通义千问 API。model 为空时使用 qwen-turbo。"""
    model_name = (model or "qwen-turbo").strip() or "qwen-turbo"
    try:
        import httpx
        resp = httpx.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return _fallback_answer(prompt, f"API HTTP {resp.status_code}")
        data = resp.json()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            return (msg.get("content") or "").strip() or _fallback_answer(prompt)
        return _fallback_answer(prompt)
    except Exception as e:
        return _fallback_answer(prompt, str(e))


def _call_openai(prompt: str) -> str:
    """OpenAI 兼容接口"""
    try:
        import httpx
        base = "https://api.openai.com/v1"
        if settings.OPENAI_API_KEY and "sk-" in (settings.OPENAI_API_KEY or ""):
            url = f"{base}/chat/completions"
            key = settings.OPENAI_API_KEY
        else:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            key = settings.DASHSCOPE_API_KEY or settings.OPENAI_API_KEY
        if not key:
            return _fallback_answer(prompt)
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code != 200:
            return _fallback_answer(prompt, f"API HTTP {resp.status_code}")
        data = resp.json()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            return (msg.get("content") or "").strip() or _fallback_answer(prompt)
        return _fallback_answer(prompt)
    except Exception as e:
        return _fallback_answer(prompt, str(e))


def _call_local_llm(prompt: str) -> str:
    """本地 Qwen 等（CPU 推理，适配 2 核 8G）"""
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_name = "Qwen/Qwen-1_8B-Chat"
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name, trust_remote_code=True
        ).to("cpu")
        response, _ = model.chat(tokenizer, prompt, history=[])
        return (response or "").strip() or _fallback_answer(prompt)
    except Exception as e:
        return _fallback_answer(prompt, str(e))


def _fallback_answer(prompt: str, reason: Optional[str] = None) -> str:
    """无 LLM 或调用失败时返回的兜底说明"""
    tip = "（暂无可用大模型，请配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY，或使用本地 LLM_MODE=local）"
    if reason:
        tip = f"（LLM 调用异常：{reason}）"
    return f"根据当前知识库内容与上下文，建议您以保险合同条款为准进行核实。本内容仅供参考，不构成投保建议。{tip}"
