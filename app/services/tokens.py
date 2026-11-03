from __future__ import annotations

from app.logging_config import audit
from app.repositories.tokens import TokenRepository
from app.repositories.users import UserRepository
from app.security import tokens as jwt_service
from app.services.errors import UnauthorizedError

_UA_MISMATCH = "Refresh-токен використано з іншого клієнта. Увійдіть повторно."


def issue_pair(
    user: dict,
    user_agent_hash: str | None,
    family_id: str | None = None,
) -> dict:
    return {
        "access_token": jwt_service.create_access_token(
            user["id"], user["username"], user["role"], user_agent_hash
        ),
        "refresh_token": jwt_service.create_refresh_token(
            user["id"], family_id=family_id, user_agent_hash=user_agent_hash
        ),
        "token_type": "bearer",
    }


def refresh(
    refresh_token: str | None,
    *,
    user_agent_hash: str,
    client_ip: str,
) -> dict:
    if not refresh_token:
        raise UnauthorizedError("Refresh-токен відсутній")

    try:
        claims = jwt_service.decode_token(refresh_token, expected_type="refresh")
    except jwt_service.TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    family_id = claims.get("fam")

    if jwt_service.is_token_revoked(claims):
        if family_id:
            TokenRepository.revoke_family(family_id, reason="replay_detected")
        audit("refresh_replay", user=claims.get("sub"), ip=client_ip)
        raise UnauthorizedError(
            "Спроба повторного використання токена (Replay Attack)! "
            "Ланцюжок токенів анульовано."
        )

    if family_id and TokenRepository.is_family_revoked(family_id):
        audit("refresh_family_revoked", family=family_id, ip=client_ip)
        raise UnauthorizedError(
            "Ланцюжок refresh-токенів відкликано. Увійдіть повторно."
        )

    if claims.get("ua") and claims["ua"] != user_agent_hash:
        if family_id:
            TokenRepository.revoke_family(family_id, reason="ua_mismatch")
        audit("refresh_ua_mismatch", user=claims.get("sub"), ip=client_ip)
        raise UnauthorizedError(_UA_MISMATCH)

    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Некоректний токен") from exc

    user = UserRepository.get_by_id(user_id)
    if not user or not user.get("is_active"):
        raise UnauthorizedError("Користувача не знайдено")

    jwt_service.revoke_refresh_token(claims, reason="rotation")
    tokens = issue_pair(user, user_agent_hash, family_id=family_id)

    audit("token_refreshed", user=user["username"], ip=client_ip)
    return tokens


def logout(refresh_token: str | None, *, client_ip: str) -> None:
    if refresh_token:
        try:
            claims = jwt_service.decode_token(
                refresh_token, expected_type="refresh"
            )
            jwt_service.revoke_refresh_token(claims, reason="logout")
        except jwt_service.TokenError:
            pass

    audit("logout", ip=client_ip)
