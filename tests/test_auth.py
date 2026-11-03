from __future__ import annotations

import pytest

from app.repositories.users import UserRepository


def test_register_rejects_weak_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "weak_user", "email": "weak@example.com", "password": "abcdefgh"},
    )
    assert response.status_code == 400
    errors = response.json()["detail"]["errors"]
    assert any("довжина" in error.lower() or "символ" in error.lower() for error in errors)


def test_register_returns_all_localized_errors(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "ab", "email": "bad", "password": "abc"},
    )
    assert response.status_code == 400

    detail = response.json()["detail"]
    errors = detail["errors"]
    field_errors = detail["field_errors"]

    assert len(errors) >= 5
    assert {"username", "email", "password"} <= set(field_errors)
    assert all(isinstance(error, str) and error.strip() for error in errors)
    assert "String should" not in response.text
    assert "valid email" not in response.text
    assert "at least" not in response.text


def test_missing_field_message_is_localized(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "someone"}
    )
    assert response.status_code == 400
    assert "Поле «Пароль» є обов'язковим" in response.text


def test_register_rejects_duplicate(client):
    payload = {
        "username": "duplicate_user",
        "email": "duplicate@example.com",
        "password": "Aa1!aaaa",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    second = client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 400
    assert "уже існує" in second.text


def test_password_is_hashed_with_salt(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "hash_user",
            "email": "hash@example.com",
            "password": "Aa1!aaaa",
        },
    )
    stored = UserRepository.get_by_username("hash_user")
    assert stored is not None
    assert stored["password_hash"] != "Aa1!aaaa"
    assert stored["password_hash"].startswith("$2b$12$")


def test_login_success_and_failure(client, user_factory):
    user = user_factory()

    bad = client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": "WrongPass1!"},
    )
    assert bad.status_code == 401

    good = client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": user["password"]},
    )
    assert good.status_code == 200
    assert {"access_token", "refresh_token", "token_type"} <= good.json().keys()


def test_login_unknown_user_same_message(client):
    first = client.post(
        "/api/v1/auth/login", json={"username": "ghost_user", "password": "Aa1!aaaa"}
    )
    second = client.post(
        "/api/v1/auth/login", json={"username": "ghost_user2", "password": "Aa1!aaaa"}
    )
    assert first.status_code == second.status_code == 401
    assert first.json()["detail"] == second.json()["detail"] == (
        "Невірне ім'я користувача або пароль."
    )


def test_sql_injection_payload_blocked(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "admin' OR '1'='1",
            "email": "sqli@example.com",
            "password": "Aa1!aaaa",
        },
    )
    assert response.status_code == 403
    assert "WAF Blocked" in response.text


def test_parameterized_query_returns_none():
    assert UserRepository.get_by_username("admin' OR '1'='1") is None


def test_inactive_user_cannot_login(client, user_factory):
    user = user_factory(active=False)

    login = client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": user["password"]},
    )
    assert login.status_code == 403

    profile = client.get("/api/v1/user/profile", headers=user["headers"])
    assert profile.status_code == 403


def test_account_locked_after_failed_attempts(client, user_factory, monkeypatch):
    from app.middleware import state

    monkeypatch.setattr(state, "RATE_LIMIT_LOGIN", 10_000)
    user = user_factory()

    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user["username"], "password": "WrongPass1!"},
        )
        assert response.status_code == 401

    locked = client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": user["password"]},
    )
    assert locked.status_code == 429
    assert "заблоковано" in locked.text.lower()
    assert "Retry-After" in locked.headers


def test_validators_reject_unsafe_username():
    from utils.validators.user_validator import UserValidator

    ok, errors = UserValidator.validate_username("<b>ab</b>")
    assert not ok
    assert errors
