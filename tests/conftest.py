from __future__ import annotations

import os
import secrets
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DATA_DIR = Path(tempfile.mkdtemp(prefix="docvault-tests-"))

# Важливо: змінні виставляються ДО імпорту config/api.
os.environ.update(
    {
        "DOCVAULT_DATA_DIR": str(TEST_DATA_DIR),
        "JWT_SECRET_KEY": secrets.token_hex(32),
        "FILE_ENCRYPTION_KEY": secrets.token_hex(32),
        "SIGNING_KEY_ENCRYPTION_KEY": secrets.token_hex(32),
        "COOKIE_SECURE": "false",
        "RATE_LIMIT_ENABLED": "true",
        "WAF_ENABLED": "true",
        "DEBUG": "false",
    }
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.middleware import state as security_state  # noqa: E402
from app.security import tokens as jwt_service  # noqa: E402

# Глобальний ліміт входу підвищуємо, щоб фікстури не впиралися у 5/хв.
security_state.RATE_LIMIT_LOGIN = 10_000
security_state.RATE_LIMIT_GENERAL = 10_000


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    import api

    with TestClient(api.app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_security_state(client):
    security_state.reset_state()
    # Сесійний TestClient тримає cookie між тестами — ізолюємо їх.
    client.cookies.clear()
    yield
    security_state.reset_state()
    client.cookies.clear()


@pytest.fixture
def user_factory(client):
    created: list[dict] = []

    def create(password: str = "Aa1!aaaa", *, active: bool = True) -> dict:
        suffix = uuid.uuid4().hex[:8]
        username = f"user_{suffix}"
        email = f"{username}@example.com"

        response = client.post(
            "/api/v1/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        assert response.status_code == 201, response.text

        login = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert login.status_code == 200, login.text
        payload = login.json()

        record = {
            "username": username,
            "email": email,
            "password": password,
            "user_id": int(jwt_service.decode_token(payload["access_token"])["sub"]),
            "access_token": payload["access_token"],
            "refresh_token": payload["refresh_token"],
            "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        }

        if not active:
            from app.repositories.users import UserRepository

            UserRepository.set_active(record["user_id"], False)

        created.append(record)
        return record

    return create


@pytest.fixture
def sample_pdf() -> bytes:
    return b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n%%EOF\n"
