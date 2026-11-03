import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.rate_limiter import rate_limiter
from utils.waf_filter import inspect_request_data

# Словник для збереження тимчасово заблокованих IP: { "ip": unblock_timestamp }
banned_ips = {}
BAN_DURATION_SECONDS = 300  # Інтервал блокування: 5 хвилин (300 секунд)

def is_ip_banned(client_ip: str) -> tuple[bool, int]:
    current_time = time.time()
    if client_ip in banned_ips:
        unblock_time = banned_ips[client_ip]
        if current_time < unblock_time:
            remaining = int(unblock_time - current_time) + 1
            return True, remaining
        else:
            # Час бану минув — вилучаємо IP із Greylist
            del banned_ips[client_ip]
    return False, 0

def ban_ip(client_ip: str, duration: int = BAN_DURATION_SECONDS):
    banned_ips[client_ip] = time.time() + duration


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "127.0.0.1"
        path = request.url.path
        query_string = request.url.query

        # 0. Перевірка: чи IP заблоковано в Greylist за попередні атаки
        banned, remaining_sec = is_ip_banned(client_ip)
        if banned:
            response = JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "error": "Forbidden",
                    "message": f"Ваш IP заблоковано WAF через шкідливу активність. Залишилось почекати: {remaining_sec} сек."
                }
            )
            return self._add_security_headers(response, path)

        # 1. Читання тіла запиту без його втрати для подальших обробників
        body_bytes = await request.body()
        body_text = body_bytes.decode("utf-8", errors="ignore")

        async def receive():
            return {"type": "http.request", "body": body_bytes}

        request = Request(request.scope, receive=receive)

        # 2. Перевірка WAF (сигнатурний аналіз)
        is_attack, attack_desc = inspect_request_data(path, query_string, body_text, client_ip)
        if is_attack:
            # 💥 ДОДАНО: Блокування IP в Greylist на 5 хвилин (300 сек)
            ban_ip(client_ip, duration=BAN_DURATION_SECONDS)

            response = JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "error": "Forbidden",
                    "message": f"WAF Blocked: Виявлено шкідливий запит ({attack_desc}). Ваш IP заблоковано на 5 хвилин."
                }
            )
            return self._add_security_headers(response, path)

        # 3. Перевірка Rate Limiter
        if path in ["/api/v1/auth/login", "/login"]:
            limit, window = 5, 60
            endpoint_key = "auth_login"
        else:
            limit, window = 60, 60
            endpoint_key = "general_api"

        is_limited, retry_after = rate_limiter.is_rate_limited(client_ip, endpoint_key, limit, window)
        if is_limited:
            response = JSONResponse(
                status_code=429,
                content={
                    "status": "error",
                    "error": "Too Many Requests",
                    "message": f"Перевищено ліміт запитів. Спробуйте через {retry_after} секунд."
                },
                headers={"Retry-After": str(retry_after)}
            )
            return self._add_security_headers(response, path)

        # 4. Виконання запиту та додавання захисних заголовків
        response: Response = await call_next(request)
        return self._add_security_headers(response, path)

    def _add_security_headers(self, response: Response, path: str) -> Response:
        if path.startswith("/docs") or path.startswith("/openapi.json"):
            script_policy = "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        else:
            script_policy = "script-src 'self' https://cdn.jsdelivr.net; "

        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            + script_policy +
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
            "object-src 'none'; "
            "frame-ancestors 'none';"
        )
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response