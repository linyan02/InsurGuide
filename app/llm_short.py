"""
短文本 LLM 调用 - 供意图识别、问题改写等场景使用（小 token、低延迟）
与 answer_engine 的长答案生成解耦，便于按业务选择调用方式
"""
from typing import Optional

from config import settings


def call(prompt: str, max_tokens: int = 128) -> str:
    """
    调用大模型生成短文本（意图标签、改写句等）。
    使用与 answer_engine 相同的 API 配置（DASHSCOPE / OpenAI）。
    无可用 API 时返回空字符串。
    """
    try:
        import httpx
        # 优先用通义千问，若配置了 OpenAI 且 key 以 sk- 开头则走 OpenAI 地址
        api_key = getattr(settings, "DASHSCOPE_API_KEY", None) or getattr(
            settings, "OPENAI_API_KEY", None
        )
        if not api_key:
            return ""
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        if getattr(settings, "OPENAI_API_KEY", None) and (
            (settings.OPENAI_API_KEY or "").startswith("sk-")
        ):
            url = "https://api.openai.com/v1/chat/completions"
            api_key = settings.OPENAI_API_KEY
        body = {
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if "openai.com" in url:
            body["model"] = "gpt-3.5-turbo"
        resp = httpx.post(url, headers=headers, json=body, timeout=15)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            msg = choices[0].get("message") or {}
            return (msg.get("content") or "").strip()
    except Exception:
        pass
    return ""


def is_available() -> bool:
    """是否有可用的短文本 LLM API"""
    return bool(
        getattr(settings, "DASHSCOPE_API_KEY", None)
        or getattr(settings, "OPENAI_API_KEY", None)
    )
