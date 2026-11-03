from __future__ import annotations

from app.middleware import state as middleware
from app.middleware.waf import inspect_payload


def test_security_headers_present(client, user_factory):
    user = user_factory()
    response = client.get("/api/v1/user/profile", headers=user["headers"])

    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    assert response.headers["Cache-Control"] == "no-store"


def test_csp_is_strict_for_app(client):
    response = client.get("/")
    csp = response.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_csp_allows_swagger_only_for_docs(client):
    csp = client.get("/docs").headers["Content-Security-Policy"]
    assert "cdn.jsdelivr.net" in csp


def test_login_cookie_flags(client, user_factory):
    user = user_factory()
    response = client.post(
        "/api/v1/auth/login",
        json={"username": user["username"], "password": user["password"]},
    )
    cookies = response.headers.get_list("set-cookie")
    access_cookie = next(cookie for cookie in cookies if cookie.startswith("access_token="))

    assert "HttpOnly" in access_cookie
    assert "SameSite=strict" in access_cookie.lower() or "samesite=strict" in access_cookie.lower()
    assert "Path=/" in access_cookie


def test_csrf_required_for_cookie_auth(client, user_factory):
    user = user_factory()
    # Автентифікація саме cookie, без заголовка Authorization.
    client.cookies.set("access_token", user["access_token"], path="/")
    client.cookies.set("csrf_token", "csrf-value", path="/")

    blocked = client.post(
        "/api/v1/documents/upload",
        files={"file": ("csrf.txt", b"data", "text/plain")},
    )
    assert blocked.status_code == 403
    assert "CSRF" in blocked.text

    allowed = client.post(
        "/api/v1/documents/upload",
        headers={"X-CSRF-Token": "csrf-value"},
        files={"file": ("csrf.txt", b"data", "text/plain")},
    )
    assert allowed.status_code == 201


def test_rate_limit_login(client, monkeypatch):
    monkeypatch.setattr(middleware, "RATE_LIMIT_LOGIN", 3)
    middleware.reset_state()

    statuses = []
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "bruteforce", "password": "WrongPass1!"},
        )
        statuses.append(response.status_code)
        if response.status_code == 429:
            assert "Retry-After" in response.headers
            assert int(response.headers["Retry-After"]) >= 1

    assert 429 in statuses
    assert statuses[-1] == 429


def test_rate_limit_does_not_apply_to_docs(client, monkeypatch):
    monkeypatch.setattr(middleware, "RATE_LIMIT_GENERAL", 1)
    middleware.reset_state()

    for _ in range(5):
        assert client.get("/docs").status_code == 200


def test_path_traversal_blocks_and_bans(client):
    response = client.get("/api/v1/user/profile?file=../../etc/passwd")
    assert response.status_code == 403
    assert "Path Traversal" in response.text

    # Greylist: наступний навіть легітимний запит від цього IP відхиляється.
    banned = client.get("/api/v1/user/profile")
    assert banned.status_code == 403
    assert "заблоковано" in banned.text


def test_multipart_upload_is_not_blocked_by_waf(client, user_factory):
    user = user_factory()
    response = client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        files={"file": ("upload.txt", b"text with a -- b", "text/plain")},
    )
    assert response.status_code in (201, 400)
    assert response.status_code != 403


def test_waf_signature_catalog():
    assert inspect_payload("../../etc/passwd")[0] is True
    assert inspect_payload("1 UNION SELECT password FROM users")[0] is True
    assert inspect_payload("<script>alert(1)</script>")[0] is True
    assert inspect_payload("normal user text")[0] is False


def test_xss_text_is_sanitized_not_blocked(client, user_factory):
    from app.security.sanitizer import sanitize_user_input

    payload = "<script>alert('XSS')</script>"
    cleaned = sanitize_user_input(payload)
    assert "<script" not in cleaned
    assert "alert('XSS')" in cleaned
