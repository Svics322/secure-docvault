from __future__ import annotations

import logging
import time
import uuid
from urllib.parse import unquote

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import (
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_GENERAL_WINDOW,
    RATE_LIMIT_LOGIN_WINDOW,
    WAF_BAN_SECONDS,
    WAF_ENABLED,
    WAF_MAX_BODY_INSPECTION,
)
from app.logging_config import audit
from app.middleware import state
from app.middleware.client_ip import get_client_ip
from app.middleware.csrf import UNSAFE_METHODS, csrf_failed
from app.middleware.headers import add_security_headers
from app.middleware.limiter import rate_limiter
from app.middleware.waf import inspect_request_data, should_inspect_body

logger = logging.getLogger("middleware")

LOGIN_PATHS = {"/api/v1/auth/login", "/login"}
SKIP_RATE_LIMIT_PREFIXES = ("/static", "/docs", "/redoc", "/openapi.json", "/favicon")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        client_ip = get_client_ip(request)
        path = unquote(request.url.path)
        request_id = str(uuid.uuid4())

        banned, remaining = state.is_ip_banned(client_ip)
        if banned:
            audit("waf_ip_banned_request", ip=client_ip, path=path)
            response = self._error(
                403,
                "Ваш IP заблоковано WAF через шкідливу активність. "
                f"Залишилось почекати: {remaining} сек.",
            )
            return self._finalize(response, path, request_id, started, client_ip)

        if request.method == "OPTIONS":
            response = await call_next(request)
            return self._finalize(response, path, request_id, started, client_ip)

        request, waf_response = await self._inspect_waf(request, path, client_ip)
        if waf_response is not None:
            return self._finalize(waf_response, path, request_id, started, client_ip)

        limited, retry_after = self._rate_limited(path, client_ip)
        if limited:
            audit("rate_limit_exceeded", ip=client_ip, path=path, retry_after=retry_after)
            response = self._error(
                429,
                f"Перевищено ліміт запитів. Спробуйте через {retry_after} секунд.",
                headers={"Retry-After": str(retry_after)},
            )
            return self._finalize(response, path, request_id, started, client_ip)

        if csrf_failed(request, path):
            audit("csrf_rejected", ip=client_ip, path=path)
            response = self._error(403, "Відсутній або некоректний CSRF-токен.")
            return self._finalize(response, path, request_id, started, client_ip)

        response = await call_next(request)
        return self._finalize(response, path, request_id, started, client_ip)

    async def _inspect_waf(
        self, request: Request, path: str, client_ip: str
    ) -> tuple[Request, Response | None]:
        if not WAF_ENABLED:
            return request, None

        body_text = ""
        content_type = request.headers.get("content-type")
        content_length = request.headers.get("content-length")
        inspect_body = (
            request.method in UNSAFE_METHODS
            and path.startswith("/api/")
            and should_inspect_body(content_type)
        )
        if inspect_body:
            try:
                declared = int(content_length) if content_length else 0
            except ValueError:
                declared = 0
            if declared <= WAF_MAX_BODY_INSPECTION:
                body_bytes = await request.body()
                body_text = body_bytes.decode("utf-8", errors="ignore")

                async def receive(body: bytes = body_bytes):
                    return {"type": "http.request", "body": body, "more_body": False}

                request = Request(request.scope, receive=receive)

        is_attack, description, severity = inspect_request_data(
            path,
            request.url.query,
            body_text,
            client_ip,
            content_type=content_type,
        )
        if not is_attack:
            return request, None

        if severity == "high":
            state.ban_ip(client_ip, WAF_BAN_SECONDS)
        audit(
            "waf_block",
            ip=client_ip,
            path=path,
            attack=description,
            severity=severity,
        )
        suffix = (
            f"Ваш IP заблоковано на {WAF_BAN_SECONDS // 60} хв."
            if severity == "high"
            else "Запит відхилено."
        )
        return request, self._error(
            403,
            f"WAF Blocked: Виявлено шкідливий запит ({description}). {suffix}",
        )

    @staticmethod
    def _rate_limited(path: str, client_ip: str) -> tuple[bool, int]:
        if (
            not RATE_LIMIT_ENABLED
            or not path.startswith("/api/")
            or path.startswith(SKIP_RATE_LIMIT_PREFIXES)
        ):
            return False, 0

        if path in LOGIN_PATHS:
            limit = state.RATE_LIMIT_LOGIN
            window = RATE_LIMIT_LOGIN_WINDOW
            key = "auth_login"
        else:
            limit = state.RATE_LIMIT_GENERAL
            window = RATE_LIMIT_GENERAL_WINDOW
            key = "general_api"

        return rate_limiter.is_rate_limited(client_ip, key, limit, window)

    @staticmethod
    def _error(
        status_code: int, message: str, *, headers: dict[str, str] | None = None
    ) -> JSONResponse:
        error_titles = {
            403: "Forbidden",
            429: "Too Many Requests",
        }
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "error",
                "error": error_titles.get(status_code, "Error"),
                "message": message,
            },
            headers=headers,
        )

    @staticmethod
    def _finalize(
        response: Response,
        path: str,
        request_id: str,
        started: float,
        client_ip: str,
    ) -> Response:
        add_security_headers(response, path)
        response.headers["X-Request-ID"] = request_id

        if path.startswith("/static"):
            # Файли клієнта можуть змінюватися без зміни URL: браузер
            # має щоразу перевіряти актуальність, а не брати з кешу.
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith("/api/") or path == "/":
            response.headers["Cache-Control"] = "no-store"

        duration_ms = (time.perf_counter() - started) * 1000
        if duration_ms > 1000:
            logger.warning(
                "Повільний запит: %s %.0f ms (ip=%s, request_id=%s)",
                path,
                duration_ms,
                client_ip,
                request_id,
            )

        return response
