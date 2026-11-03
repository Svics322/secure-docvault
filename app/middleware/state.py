from __future__ import annotations

import time

from config import (
    RATE_LIMIT_GENERAL,
    RATE_LIMIT_LOGIN,
    WAF_BAN_MAX_ENTRIES,
    WAF_BAN_SECONDS,
)
from app.middleware.limiter import rate_limiter

__all__ = [
    "RATE_LIMIT_GENERAL",
    "RATE_LIMIT_LOGIN",
    "banned_ips",
    "ban_ip",
    "is_ip_banned",
    "reset_state",
]

banned_ips: dict[str, float] = {}


def _purge_bans(now: float) -> None:
    expired = [ip for ip, unblock_at in banned_ips.items() if unblock_at <= now]
    for ip in expired:
        banned_ips.pop(ip, None)


def is_ip_banned(client_ip: str) -> tuple[bool, int]:
    now = time.time()
    if len(banned_ips) > 1024:
        _purge_bans(now)

    unblock_at = banned_ips.get(client_ip)
    if unblock_at is None:
        return False, 0

    if now < unblock_at:
        return True, int(unblock_at - now) + 1

    banned_ips.pop(client_ip, None)
    return False, 0


def ban_ip(client_ip: str, duration: int = WAF_BAN_SECONDS) -> None:
    if len(banned_ips) >= WAF_BAN_MAX_ENTRIES:
        _purge_bans(time.time())
        if len(banned_ips) >= WAF_BAN_MAX_ENTRIES:
            oldest = min(banned_ips, key=banned_ips.get)
            banned_ips.pop(oldest, None)
    banned_ips[client_ip] = time.time() + duration


def reset_state() -> None:
    banned_ips.clear()
    rate_limiter.reset()
