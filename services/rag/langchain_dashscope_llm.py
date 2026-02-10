"""
LangChain 自定义 LLM：封装 DashScope 通义千问调用

目标：
- 继承 langchain_core.language_models.llms.LLM
- 内部复用现有 app.answer_engine._call_dashscope 逻辑
- 这样在 LangChain 的 Chain / Agent 中就可以像使用普通 LLM 一样使用 DashScope
"""
from typing import Any, List, Optional

from langchain_core.language_models.llms import LLM
from pydantic import Field

from app.answer_engine import _call_dashscope  # 直接复用现有 DashScope 调用实现


class DashScopeLLM(LLM):
    """
    自定义 LangChain LLM，基于现有的 _call_dashscope 实现。

    使用方式示例：
    - 在 Chain 中：
        from langchain.prompts import PromptTemplate
        from langchain.chains import LLMChain
        from services.rag.langchain_dashscope_llm import DashScopeLLM

        llm = DashScopeLLM()
        prompt = PromptTemplate.from_template("你是保险专家，请回答：{question}")
        chain = LLMChain(llm=llm, prompt=prompt)
        result = chain.run({"question": "重疾险等待期一般多长？"})
    """

    # 若将来要扩展更多控制参数，可以在这里定义（如 temperature、max_tokens 等）
    model_name: str = Field(
        default="qwen-turbo",
        description="DashScope 使用的模型名称（当前 _call_dashscope 内部固定为 qwen-turbo，仅作文档提示）。",
    )
    max_tokens: int = Field(
        default=1024,
        description="最大生成 token 数（当前由 _call_dashscope 内部控制，仅作文档提示）。",
    )

    @property
    def _llm_type(self) -> str:
        """
        返回一个标识字符串，便于在调试/日志中区分不同自定义 LLM。
        """
        return "dashscope_llm"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """
        LangChain LLM 抽象要求实现的核心方法：
        - 入参：prompt 是拼接好的大字符串（由 PromptTemplate.format 得来）
        - stop：可选的停止词列表，若出现则截断
        - 返回：模型生成的文本结果
        """
        # 直接调用项目里已经实现好的 DashScope 封装函数
        text = _call_dashscope(prompt)

        # 处理 stop tokens：如果配置了 stop，就在结果里找到第一个 stop 并截断
        if stop:
            for s in stop:
                if s and s in text:
                    text = text.split(s)[0]
                    break

        return text or ""


__all__ = ["DashScopeLLM"]

