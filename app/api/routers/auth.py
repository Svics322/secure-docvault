from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

import config as settings
from app.api.cookies import clear_auth_cookies, token_response
from app.dependencies import get_current_user
from app.middleware.client_ip import get_client_ip
from app.schemas import RefreshRequest, UserLogin, UserRegister
from app.security.tokens import hash_user_agent
from app.services import auth as auth_service
from app.services import tokens as token_service

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
@router.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister, request: Request):
    return auth_service.register(
        user.username,
        str(user.email),
        user.password,
        client_ip=get_client_ip(request),
    )


@router.post("/login")
@router.post("/api/v1/auth/login")
def login_user(payload: UserLogin, request: Request):
    user = auth_service.authenticate(
        payload.username,
        payload.password,
        client_ip=get_client_ip(request),
    )
    tokens = token_service.issue_pair(
        user, hash_user_agent(request.headers.get("user-agent"))
    )
    return token_response(tokens)


@router.post("/api/v1/auth/refresh")
def refresh_token(request: Request, payload: RefreshRequest | None = None):
    token = (payload.refresh_token if payload else None) or request.cookies.get(
        settings.REFRESH_COOKIE_NAME
    )
    tokens = token_service.refresh(
        token,
        user_agent_hash=hash_user_agent(request.headers.get("user-agent")),
        client_ip=get_client_ip(request),
    )
    return token_response(tokens)


@router.post("/api/v1/auth/logout")
@router.post("/logout")
def logout(request: Request):
    token_service.logout(
        request.cookies.get(settings.REFRESH_COOKIE_NAME),
        client_ip=get_client_ip(request),
    )
    response = JSONResponse(
        content={"status": "success", "message": "Вихід виконано"}
    )
    clear_auth_cookies(response)
    return response


@router.get("/api/v1/user/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return auth_service.get_profile(current_user)
