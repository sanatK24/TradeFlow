import pytest

pytestmark = pytest.mark.api

def test_register_success(test_app):
    response = test_app.post("/api/v1/auth/register", json={"username": "user1", "password": "password1"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["username"] == "user1"
    assert "cash_balance" in data

def test_register_duplicate_username(test_app):
    test_app.post("/api/v1/auth/register", json={"username": "user2", "password": "password1"})
    response = test_app.post("/api/v1/auth/register", json={"username": "user2", "password": "password1"})
    assert response.status_code == 400

def test_login_success(test_app):
    test_app.post("/api/v1/auth/register", json={"username": "user3", "password": "password1"})
    response = test_app.post("/api/v1/auth/token", data={"username": "user3", "password": "password1"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == "user3"
    assert "user_id" in data
    assert "cash_balance" in data

def test_login_wrong_password(test_app):
    test_app.post("/api/v1/auth/register", json={"username": "user4", "password": "password1"})
    response = test_app.post("/api/v1/auth/token", data={"username": "user4", "password": "wrong"})
    assert response.status_code == 401

def test_login_nonexistent_user(test_app):
    response = test_app.post("/api/v1/auth/token", data={"username": "nonexistent", "password": "password"})
    assert response.status_code == 401

def test_get_me_authenticated(test_app):
    test_app.post("/api/v1/auth/register", json={"username": "user5", "password": "password1"})
    res = test_app.post("/api/v1/auth/token", data={"username": "user5", "password": "password1"})
    token = res.json()["access_token"]
    response = test_app.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "user5"

def test_get_me_no_token(test_app):
    response = test_app.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_get_me_invalid_token(test_app):
    response = test_app.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401
