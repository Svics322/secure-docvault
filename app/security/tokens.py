from __future__ import annotations

import datetime
import hashlib
import logging
import uuid

import jwt

from config import (
    ACCESS_TOKEN_TTL_MINUTES,
    JWT_AUDIENCE,
    JWT_ISSUER,
    REFRESH_TOKEN_TTL_DAYS,
)
from app.repositories.tokens import TokenRepository
from app.security.secrets import load_secret

logger = logging.getLogger("security.tokens")

SECRET_KEY = load_secret(
    "JWT_SECRET_KEY",
    nbytes=32,
    hex_encoded=False,
    min_bytes=32,
)
ALGORITHM = "HS256"

_REQUIRED_CLAIMS = ["exp", "iat", "sub", "jti", "type", "iss", "aud"]


class TokenError(ValueError):
    pass


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def hash_user_agent(user_agent: str | None) -> str:
    raw = (user_agent or "unknown").encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:32]


def create_access_token(
    user_id: int,
    username: str,
    role: str,
    user_agent_hash: str | None = None,
) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "exp": now + datetime.timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        "iat": now,
        "type": "access",
    }
    if user_agent_hash:
        payload["ua"] = user_agent_hash
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    family_id: str | None = None,
    user_agent_hash: str | None = None,
) -> str:
    now = _now()
    payload = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "fam": family_id or str(uuid.uuid4()),
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "exp": now + datetime.timedelta(days=REFRESH_TOKEN_TTL_DAYS),
        "iat": now,
        "type": "refresh",
    }
    if user_agent_hash:
        payload["ua"] = user_agent_hash
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    if not token or not isinstance(token, str):
        raise TokenError("Токен відсутній")

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Термін дії токена минув (Expired Token)") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Недійсний підпис або пошкоджений токен (Invalid Token)") from exc

    if expected_type and payload.get("type") != expected_type:
        raise TokenError(
            f"Надано некоректний тип токена (очікується {expected_type})"
        )

    return payload


def token_expiry(payload: dict) -> datetime.datetime:
    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        return datetime.datetime.fromtimestamp(exp, tz=datetime.timezone.utc).replace(
            tzinfo=None
        )
    if isinstance(exp, datetime.datetime):
        return exp.replace(tzinfo=None)
    return datetime.datetime.utcnow()


def revoke_refresh_token(
    token_or_payload: str | dict, reason: str = "rotation"
) -> None:
    if isinstance(token_or_payload, str):
        payload = decode_token(token_or_payload, expected_type="refresh")
    else:
        payload = token_or_payload

    TokenRepository.revoke(
        jti=payload["jti"],
        user_id=int(payload["sub"]),
        expires_at=token_expiry(payload),
        family_id=payload.get("fam"),
        reason=reason,
    )


def is_token_revoked(token_or_payload: str | dict) -> bool:
    if isinstance(token_or_payload, str):
        payload = decode_token(token_or_payload, expected_type="refresh")
    else:
        payload = token_or_payload
    return TokenRepository.is_revoked(payload["jti"])
