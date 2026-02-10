"""
配置层：统一应用配置与常量，支持 .env 覆盖

其他模块通过「from config import settings」拿到全局配置对象，
所有可调项（数据库、Redis、RAGflow、LLM 等）都在 config.settings 里。
"""
from config.settings import settings

__all__ = ["settings"]
