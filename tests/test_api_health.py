"""
API 健康与根路径测试（不依赖数据库与外部服务）
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from config import settings


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_root(client: TestClient):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert "message" in data
    assert settings.APP_NAME in data["message"]
    assert data["version"] == settings.APP_VERSION
    assert data.get("docs") == "/docs"


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}
