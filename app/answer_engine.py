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
1. 语气口语化、亲切自然，像朋友聊天那样说，避免生硬的条款腔和公文腔；
2. 必须引用知识库内容，禁止编造信息；
3. 把专业术语用大白话解释清楚；
4. 结尾添加合规声明：本内容仅供参考，不构成投保建议，具体以保险合同条款为准。

知识库内容：
{knowledge_content}

历史上下文（已按相关性精简）：
{context}

用户问题：
{query}
"""


# 结构化意见 Prompt 模板（RAGflow 结果 LLM 再加工，输出 Markdown）
INSURANCE_OPINION_PROMPT_TEMPLATE = """
你是一位亲切专业的保险顾问，正在像朋友聊天那样解答用户的保险问题。

## 语气要求（重要）：
- **口语化**：用日常对话的方式说，别像念条款那样生硬。可以说「一般来说」「简单说就是」「举个例子」等。
- **亲切自然**：适当用「您」「咱们」等称呼，把专业内容「翻译」成普通人能听懂的话。
- **避免生硬**：不要堆砌「依据」「根据」「上述」等公文腔；少用「需」「应」「须」等命令式表述。
- **通俗易懂**：遇到免赔额、除外责任等概念时，用一两句大白话解释清楚。

## 输出要求（必须使用 Markdown 格式）：
1. **## 核心结论**：1-2 句话直接回答，像在跟朋友说结论一样。
2. **## 详细说明**：分点展开（用 - 或 1. 2. ），基于知识库讲清楚，禁止编造。
3. **## 注意事项**：用轻松口吻提醒需要注意的地方（如有），别写得像法律文书。
4. **合规声明**：结尾必须添加：本内容仅供参考，不构成投保建议，具体以保险合同条款为准。

## 格式规范：
- 使用标准 Markdown：标题用 ##、###，列表用 - 或数字，强调用 **加粗**
- 引用条款原文时用 > 引用块，但解释部分用口语
- 保持信息准确，但表达要有人情味

## 知识库内容：
{knowledge_content}

## 历史上下文（已按相关性精简）：
{context}

## 用户问题：
{query}

请直接输出结构化意见（Markdown），不要输出其他前缀或说明。
"""


# 保障重叠度透视镜专用 Prompt 模板
COVERAGE_OVERLAP_PROMPT_TEMPLATE = """你是保障分析专家。基于检索到的知识库内容与预分析结果，对用户的保障重叠问题给出结构化分析。

## 输出要求（必须 Markdown）
1. **## 智保灵犀分析结果**
2. **结论：** 一句话（支持/反驳经纪人建议 + 简要理由）
3. **## 保障重叠透视表**
   | 风险场景 | 您的现有防线 | {pending_insurance}的作用 | 重叠判定 |
   | --- | --- | --- | --- |
   （根据下方预分析结果的 overlap_matrix 填充表格行，每行对应一个风险场景）
4. **## 专家建议** 结合预分析结果的 recommendation（{recommendation}）给出【买/不买/换】建议及理由
5. 合规声明：本内容仅供参考，不构成投保建议，具体以保险合同条款为准。

## 知识库内容
{knowledge_content}

## 预分析结果（已计算）
{analysis_result}

## 用户现有保障
{existing_coverage}

## 待购险种
{pending_insurance}

## 用户问题
{query}
"""


# 医疗条款解析专用 Prompt 模板
CLAUSE_PARSE_PROMPT_TEMPLATE = """你是专业的保险条款解读顾问。请基于以下知识库内容与用户提供的条款，回答用户问题。

## 输出要求（必须 Markdown）
1. **## 智保灵犀·条款解读**
2. **您的问题：** 简要复述
3. **条款依据：** 若知识库中有相关原文，请用引用块标注
4. **解读：** 结构化、易懂的解读
5. 结尾附：本解读仅供参考，不构成法律或投保建议，具体以保险合同条款为准。

## 知识库内容
{knowledge_content}

## 用户提供的条款（如有）
{clause_text}

## 用户问题
{query}
"""


CLAUSE_EXTRACT_PROMPT = """请从以下保险条款内容中抽取以下关键要素，以 JSON 返回。若某要素未在条款中明确提及，该字段填 null。

要素：
- deductible: 免赔额（如「1万元/年」，简洁表述）
- waiting_period: 等待期（如「30天」）
- renewal: 续保条件（如「非保证续保」「保证续保20年」）
- exclusions: 责任免除要点（2-3 条，每条不超过 30 字，用分号分隔）

条款内容：
{clause_content}

仅输出 JSON，不要其他说明。格式示例：{"deductible":"1万元/年","waiting_period":"30天","renewal":"非保证续保","exclusions":"既往症；故意行为"}"""


def extract_clause_structured(clause_content: str, model: Optional[str] = None) -> Dict[str, Optional[str]]:
    """从条款文本中抽取关键要素。若抽取失败返回空 dict。LLM 超时/网络异常时静默返回 {}，不打断主流程。"""
    if not clause_content or len(clause_content.strip()) < 50:
        return {}
    content = clause_content[:8000] if len(clause_content) > 8000 else clause_content
    prompt = CLAUSE_EXTRACT_PROMPT.format(clause_content=content)
    try:
        raw = call_light_llm(prompt, model=model)
        if not raw or "{" not in raw:
            return {}
        start = raw.index("{")
        end = raw.rindex("}") + 1
        obj = json.loads(raw[start:end])
        return {
            "deductible": obj.get("deductible"),
            "waiting_period": obj.get("waiting_period"),
            "renewal": obj.get("renewal"),
            "exclusions": obj.get("exclusions"),
        }
    except (json.JSONDecodeError, ValueError, Exception):
        return {}


def _format_clause_structured_table(extracted: Dict[str, Optional[str]]) -> str:
    """将抽取结果格式化为 Markdown 表格。"""
    d = extracted.get("deductible") or "未在条款中明确"
    w = extracted.get("waiting_period") or "未在条款中明确"
    r = extracted.get("renewal") or "未在条款中明确"
    e = extracted.get("exclusions") or "未在条款中明确"
    return """
---
## 关键要素速览

| 免赔额 | 等待期 | 续保条件 | 责任免除要点 |
| --- | --- | --- | --- |
| {deductible} | {waiting_period} | {renewal} | {exclusions} |
""".format(deductible=d, waiting_period=w, renewal=r, exclusions=e)


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


def _extract_images_and_cases(ragflow_result: Dict[str, Any]) -> str:
    """
    解析 RAGflow 返回的图片元数据与案例，生成 Markdown 富文本块。
    支持 metadatas 中的 image_url、img_url、type: case 等字段。
    """
    metadatas = ragflow_result.get("metadatas") or []
    documents = ragflow_result.get("documents") or []
    blocks: List[str] = []
    for i, meta in enumerate(metadatas):
        if not isinstance(meta, dict):
            continue
        # 图片：常见字段 image_url, img_url, image
        img_url = meta.get("image_url") or meta.get("img_url") or meta.get("image")
        if img_url and isinstance(img_url, str) and img_url.startswith(("http", "/")):
            blocks.append(f"\n\n![图片]({img_url})\n")
        # 案例：type 为 case 的片段，封装为引用块
        chunk_type = meta.get("type") or meta.get("chunk_type")
        if chunk_type == "case" and i < len(documents):
            content = documents[i] if isinstance(documents[i], str) else str(documents[i])
            if content.strip():
                blocks.append(f"\n\n> **相似案例**\n> {content}\n")
    return "\n".join(blocks) if blocks else ""


def enrich_answer_with_rich_content(answer: str, ragflow_result: Dict[str, Any]) -> str:
    """
    将 RAGflow 返回的图片、案例追加到答案，生成富文本 Markdown。
    """
    extra = _extract_images_and_cases(ragflow_result)
    if not extra:
        return answer
    return answer.rstrip() + "\n\n" + extra


def generate_answer(
    query: str,
    ragflow_result: Dict[str, Any],
    context: List[Dict[str, Any]],
    *,
    do_compliance: bool = True,
    model: Optional[str] = None,
    intent_name: Optional[str] = None,
    coverage_slots: Optional[Dict[str, Any]] = None,
    analysis_result: Optional[Dict[str, Any]] = None,
    clause_text: Optional[str] = None,
    clause_context: Optional[Dict[str, Any]] = None,
    context_count: int = 0,
) -> str:
    """
    结合 RAGflow 检索结果与历史上下文生成答案。do_compliance=True 时会调用合规检测并替换违规词。
    model：DashScope 模型名，如 qwen-turbo、qwen-plus，空则用默认。
    intent_name=coverage_overlap 且 analysis_result 有值时，使用保障重叠度专用模板。
    """
    knowledge_content = build_knowledge_content(ragflow_result)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"

    if intent_name == "coverage_overlap" and analysis_result is not None:
        slots = coverage_slots or {}
        existing = slots.get("existing_coverage_list") or []
        pending = slots.get("pending_insurance") or "待购险种"
        analysis_str = json.dumps(analysis_result, ensure_ascii=False, indent=2)
        existing_str = json.dumps(existing, ensure_ascii=False)
        recommendation = analysis_result.get("recommendation", "视情况而定")
        prompt = COVERAGE_OVERLAP_PROMPT_TEMPLATE.format(
            knowledge_content=knowledge_content,
            analysis_result=analysis_str,
            existing_coverage=existing_str,
            pending_insurance=pending,
            query=query,
            recommendation=recommendation,
        )
    elif intent_name == "clause_parse":
        clause_str = clause_text or "（未提供，仅依据知识库）"
        prompt = CLAUSE_PARSE_PROMPT_TEMPLATE.format(
            knowledge_content=knowledge_content,
            clause_text=clause_str,
            query=query,
        )
    else:
        template = (
            INSURANCE_OPINION_PROMPT_TEMPLATE
            if getattr(settings, "ANSWER_USE_OPINION_FORMAT", True)
            else INSURANCE_PROMPT_TEMPLATE
        )
        prompt = template.format(
            knowledge_content=knowledge_content,
            context=context_str,
            query=query,
        )
    answer = call_light_llm(prompt, model=model)
    if intent_name == "clause_parse" and context_count <= 1 and clause_text and len(clause_text.strip()) > 50:
        extracted = extract_clause_structured(clause_text, model=model)
        if extracted:
            answer = answer.rstrip() + _format_clause_structured_table(extracted)
    if do_compliance:
        answer, _ = check_and_mask(answer)
    answer = enrich_answer_with_rich_content(answer, ragflow_result)
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


# ---------- 流式答案生成（供 SSE 接口使用） ----------


def _call_dashscope_stream(prompt: str, model: Optional[str] = None):
    """
    流式调用 DashScope 兼容模式 API，yield 每个 content delta。
    仅当 DASHSCOPE_API_KEY 配置时支持；未配置时 yield 兜底说明。
    """
    model_name = (model or "qwen-turbo").strip() or "qwen-turbo"
    api_key = getattr(settings, "DASHSCOPE_API_KEY", None)
    if not api_key:
        fallback = _fallback_answer(prompt, "未配置 DASHSCOPE_API_KEY，流式回复不可用")
        yield fallback
        return
    try:
        import httpx
        with httpx.stream(
            "POST",
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 1024,
            },
            timeout=60.0,
        ) as resp:
            if resp.status_code != 200:
                yield _fallback_answer(prompt, f"API HTTP {resp.status_code}")
                return
            for line in resp.iter_lines():
                if not line or not line.strip():
                    continue
                if line.startswith("data: "):
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        choices = obj.get("choices") or []
                        if choices and isinstance(choices[0], dict):
                            delta = choices[0].get("delta") or {}
                            content = delta.get("content")
                            if content:
                                yield content
                    except (json.JSONDecodeError, TypeError):
                        pass
    except Exception as e:
        yield _fallback_answer(prompt, str(e))


def generate_answer_stream(
    query: str,
    ragflow_result: Dict[str, Any],
    context: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    intent_name: Optional[str] = None,
    coverage_slots: Optional[Dict[str, Any]] = None,
    analysis_result: Optional[Dict[str, Any]] = None,
    clause_text: Optional[str] = None,
    clause_context: Optional[Dict[str, Any]] = None,
):
    """
    流式生成答案，yield 每个文本片段。
    与 generate_answer 使用相同 prompt 构建逻辑，仅 LLM 调用改为流式。
    """
    knowledge_content = build_knowledge_content(ragflow_result)
    context_str = json.dumps(context, ensure_ascii=False) if context else "无"

    if intent_name == "coverage_overlap" and analysis_result is not None:
        slots = coverage_slots or {}
        existing = slots.get("existing_coverage_list") or []
        pending = slots.get("pending_insurance") or "待购险种"
        analysis_str = json.dumps(analysis_result, ensure_ascii=False, indent=2)
        existing_str = json.dumps(existing, ensure_ascii=False)
        recommendation = analysis_result.get("recommendation", "视情况而定")
        prompt = COVERAGE_OVERLAP_PROMPT_TEMPLATE.format(
            knowledge_content=knowledge_content,
            analysis_result=analysis_str,
            existing_coverage=existing_str,
            pending_insurance=pending,
            query=query,
            recommendation=recommendation,
        )
    elif intent_name == "clause_parse":
        clause_str = clause_text or "（未提供，仅依据知识库）"
        prompt = CLAUSE_PARSE_PROMPT_TEMPLATE.format(
            knowledge_content=knowledge_content,
            clause_text=clause_str,
            query=query,
        )
    else:
        template = (
            INSURANCE_OPINION_PROMPT_TEMPLATE
            if getattr(settings, "ANSWER_USE_OPINION_FORMAT", True)
            else INSURANCE_PROMPT_TEMPLATE
        )
        prompt = template.format(
            knowledge_content=knowledge_content,
            context=context_str,
            query=query,
        )

    for chunk in _call_dashscope_stream(prompt, model=model):
        yield chunk
