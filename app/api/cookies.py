from __future__ import annotations

import secrets

from fastapi import Response
from fastapi.responses import JSONResponse

import config as settings


def set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    common = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
    }
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME,
        access_token,
        max_age=settings.ACCESS_TOKEN_TTL_MINUTES * 60,
        path="/",
        **common,
    )
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
        path=settings.REFRESH_COOKIE_PATH,
        **common,
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        secrets.token_urlsafe(32),
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(
        settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH
    )
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


def token_response(tokens: dict) -> JSONResponse:
    payload = dict(tokens)
    payload["expires_in"] = settings.ACCESS_TOKEN_TTL_MINUTES * 60
    response = JSONResponse(content=payload)
    set_auth_cookies(
        response, tokens["access_token"], tokens["refresh_token"]
    )
    return response
