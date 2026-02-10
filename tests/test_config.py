"""
配置层单元测试
"""
import pytest

from config import settings
from config.constants import ALL_INTENTS, INTENT_LABELS_CN


def test_settings_load():
    assert settings.APP_NAME == "InsurGuide"
    assert settings.APP_VERSION
    assert isinstance(settings.DEBUG, bool)


def test_get_violation_words_list():
    words = settings.get_violation_words_list()
    assert isinstance(words, list)


def test_constants_intents():
    assert "retrieval" in ALL_INTENTS
    assert "claims" in ALL_INTENTS
    assert "other" in ALL_INTENTS


def test_intent_labels_cn():
    assert INTENT_LABELS_CN.get("claims") == "理赔"
    assert INTENT_LABELS_CN.get("other") == "其他"
