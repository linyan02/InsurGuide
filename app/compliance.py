"""
合规校验模块 - 保险领域违规词检测与屏蔽
产品文档：内置违规词库，实时检测并替换为 [违规表述已屏蔽]，并记录合规日志
"""
from typing import List, Tuple

from config import settings


def get_violation_words() -> List[str]:
    """从配置获取违规词列表，支持通过环境变量动态更新"""
    return settings.get_violation_words_list()


def check_and_mask(answer: str) -> Tuple[str, bool]:
    """
    检测答案中的违规表述并屏蔽。
    返回 (处理后的答案, 是否发生过违规)
    """
    words = get_violation_words()
    if not words:
        return answer, False
    violated = False
    for word in words:
        if word and word in answer:
            answer = answer.replace(word, "[违规表述已屏蔽]")
            violated = True
    return answer, violated


def add_violation_words(extra_words: List[str]) -> None:
    """
    运行时追加违规词（仅当前进程生效，重启后失效）。
    当前实现为占位：违规词来自配置 VIOLATION_WORDS，若需动态扩展可在此维护进程内列表并与 get_violation_words 合并。
    """
    pass
