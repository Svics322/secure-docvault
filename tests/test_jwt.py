from __future__ import annotations

import jwt
import pytest

from app.security import tokens as jwt_service
from config import JWT_AUDIENCE, JWT_ISSUER


def test_profile_requires_token(client):
    assert client.get("/api/v1/user/profile").status_code == 401


def test_profile_with_valid_token(client, user_factory):
    user = user_factory()
    response = client.get("/api/v1/user/profile", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["user_data"]["username"] == user["username"]


def test_tampered_token_rejected(client, user_factory):
    user = user_factory()
    header, payload, signature = user["access_token"].split(".")
    forged_payload = payload[:-2] + ("AA" if not payload.endswith("AA") else "BB")
    forged = f"{header}.{forged_payload}.{signature}"

    response = client.get(
        "/api/v1/user/profile", headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


def test_alg_none_rejected(client, user_factory):
    user = user_factory()
    forged = jwt.encode(
        {
            "sub": str(user["user_id"]),
            "username": user["username"],
            "role": "admin",
            "type": "access",
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "jti": "forged",
        },
        key="",
        algorithm="none",
    )
    response = client.get(
        "/api/v1/user/profile", headers={"Authorization": f"Bearer {forged}"}
    )
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_as_access(client, user_factory):
    user = user_factory()
    response = client.get(
        "/api/v1/user/profile",
        headers={"Authorization": f"Bearer {user['refresh_token']}"},
    )
    assert response.status_code == 401
    assert "тип токена" in response.text.lower()


def test_refresh_rotation_and_replay_detection(client, user_factory):
    user = user_factory()
    old_refresh = user["refresh_token"]

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200, first.text
    new_refresh = first.json()["refresh_token"]
    assert new_refresh != old_refresh

    # Повторне використання старого токена = атака перехоплення.
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401
    assert "Replay" in replay.text

    # Весь ланцюжок після replay вважається скомпрометованим.
    chained = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert chained.status_code == 401


def test_refresh_keeps_identity(client, user_factory):
    user = user_factory()
    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]}
    )
    assert refreshed.status_code == 200

    claims = jwt_service.decode_token(refreshed.json()["access_token"])
    assert claims["username"] == user["username"]
    assert claims["role"] == "user"


def test_logout_revokes_refresh_token(client, user_factory):
    user = user_factory()
    client.cookies.set("refresh_token", user["refresh_token"], path="/api/v1/auth")

    assert client.post("/api/v1/auth/logout").status_code == 200

    after = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": user["refresh_token"]}
    )
    assert after.status_code == 401


def test_jwt_requires_issuer_and_audience():
    token = jwt.encode(
        {"sub": "1", "type": "access", "jti": "x", "exp": 9999999999, "iat": 1},
        jwt_service.SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(jwt_service.TokenError):
        jwt_service.decode_token(token)


def test_revocation_survives_in_database(user_factory):
    from app.repositories.tokens import TokenRepository

    user = user_factory()
    claims = jwt_service.decode_token(user["refresh_token"], expected_type="refresh")
    jwt_service.revoke_refresh_token(claims, reason="test")

    # Нове підключення до БД бачить відкликання — стан не тримається в пам'яті.
    assert TokenRepository.is_revoked(claims["jti"]) is True
