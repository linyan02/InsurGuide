"""
专业版/标准版与 DashScope 模型名映射

前端传入 model_plan（pro | standard），本模块提供统一解析，
供 pipeline、langchain_chain、answer_engine 使用，便于后续扩展模型或版本。
"""
from typing import Optional


def get_dashscope_model_for_plan(model_plan: Optional[str]) -> str:
    """
    根据前端 model_plan 返回 DashScope 使用的模型名。
    - pro：专业版，使用 qwen-plus
    - standard 或空：标准版，使用 qwen-turbo
    """
    if model_plan == "pro":
        return "qwen-plus"
    return "qwen-turbo"
