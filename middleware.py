from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        if request.url.path.startswith("/docs") or request.url.path.startswith("/openapi.json"):
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
        
        # Захист від Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Захист від MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Примусовий HTTPS (HSTS) на 1 рік
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Контроль передачі реферера
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response