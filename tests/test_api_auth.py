"""
认证 API 测试：注册、登录、获取当前用户
使用 conftest 中的测试 DB（SQLite 内存）
"""
import pytest
from fastapi.testclient import TestClient


def test_register(client: TestClient):
    r = client.post(
        "/api/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_register_duplicate_username(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "dup", "email": "a@b.com", "password": "pass123"},
    )
    r = client.post(
        "/api/auth/register",
        json={"username": "dup", "email": "c@d.com", "password": "pass456"},
    )
    assert r.status_code == 400
    assert "用户名" in r.json().get("detail", "")


def test_login(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "loginuser", "email": "login@example.com", "password": "secret123"},
    )
    r = client.post(
        "/api/auth/login",
        data={"username": "loginuser", "password": "secret123"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


def test_login_wrong_password(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "u2", "email": "u2@x.com", "password": "right"},
    )
    r = client.post("/api/auth/login", data={"username": "u2", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_me_with_token(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "meuser", "email": "me@x.com", "password": "pass"},
    )
    login = client.post("/api/auth/login", data={"username": "meuser", "password": "pass"})
    token = login.json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "meuser"
