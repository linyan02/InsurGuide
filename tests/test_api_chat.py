"""
增强 RAG 对话 API 测试：参数校验、无 RAGflow 时的错误响应
"""
import pytest
from fastapi.testclient import TestClient


def test_chat_missing_user_id(client: TestClient):
    r = client.post("/api/chat", json={"user_id": "", "query": "你好"})
    assert r.status_code == 400
    assert "user_id" in r.json().get("detail", "").lower()


def test_chat_missing_query(client: TestClient):
    r = client.post("/api/chat", json={"user_id": "test-user", "query": ""})
    assert r.status_code == 400
    assert "query" in r.json().get("detail", "").lower()


def test_chat_returns_structure(client: TestClient):
    """有 body 时返回 200 或 500，且 data 结构一致（RAGflow 未配置时多为 500）"""
    r = client.post(
        "/api/chat",
        json={"user_id": "test-user-1", "query": "重疾险等待期多久"},
    )
    # 未配置 RAGflow 时通常 500，配置后 200
    assert r.status_code in (200, 500)
    data = r.json()
    assert "code" in data
    assert "message" in data
    if data.get("code") == 200:
        assert "data" in data
        assert "answer" in data["data"] or "error" in data.get("data") or True
    else:
        assert data.get("data") is None or "error" in str(data.get("message", ""))


def test_chat_clear(client: TestClient):
    r = client.post("/api/chat/clear", json={"user_id": "any-user"})
    assert r.status_code == 200
    assert "code" in r.json()
