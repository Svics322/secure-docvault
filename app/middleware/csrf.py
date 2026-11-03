from __future__ import annotations

import secrets

from fastapi import Request

from config import ACCESS_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

AUTH_PATHS = {
    "/api/v1/auth/login",
    "/login",
    "/api/v1/auth/register",
    "/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/logout",
}


def csrf_failed(request: Request, path: str) -> bool:
    if request.method not in UNSAFE_METHODS:
        return False
    if not path.startswith("/api/"):
        return False
    if path in AUTH_PATHS:
        return False
    if "authorization" in request.headers:
        return False
    if not request.cookies.get(ACCESS_COOKIE_NAME):
        return False

    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    header_token = request.headers.get(CSRF_HEADER_NAME, "")
    if not cookie_token or not header_token:
        return True
    return not secrets.compare_digest(cookie_token, header_token)
