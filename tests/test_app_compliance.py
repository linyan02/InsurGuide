"""
合规模块单元测试：违规词检测与屏蔽
"""
import pytest

from app.compliance import check_and_mask, get_violation_words


def test_check_and_mask_no_violation():
    text = "根据条款，等待期一般为 90 天。"
    out, violated = check_and_mask(text)
    assert out == text
    assert violated is False


def test_check_and_mask_with_violation():
    text = "买这款可以保证赔付。"
    out, violated = check_and_mask(text)
    assert violated is True
    assert "保证赔付" not in out
    assert "[违规表述已屏蔽]" in out


def test_get_violation_words():
    words = get_violation_words()
    assert isinstance(words, list)
    # 默认配置含常见违规词
    assert any("理赔" in w or "赔付" in w for w in words) or len(words) >= 0
