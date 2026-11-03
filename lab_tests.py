"""Перевірка сценаріїв лабораторних робіт №1–4 для Secure DocVault.

Запуск (сервер має працювати з TRUST_PROXY=true):
    python lab_tests.py http://127.0.0.1:8020

Кожна група тестів імітує окремого клієнта через X-Forwarded-For, щоб
блокування WAF та Rate Limiter не впливали на сусідні перевірки.
"""

from __future__ import annotations

import re
import sys
import uuid

import requests

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip(
    "/"
)
TIMEOUT = 5

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    results.append((name, bool(condition), detail))
    mark = "OK  " if condition else "FAIL"
    print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))


def headers(ip: str, token: str | None = None) -> dict[str, str]:
    values = {"X-Forwarded-For": ip}
    if token:
        values["Authorization"] = f"Bearer {token}"
    return values


def new_user(prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"{prefix}_{suffix}"
    return {
        "username": username,
        "email": f"{username}@example.com",
        "password": "Aa1!aaaa",
    }


def register(ip: str, user: dict[str, str]) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json=user,
        headers=headers(ip),
        timeout=TIMEOUT,
    )


def login(ip: str, user: dict[str, str]) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": user["username"], "password": user["password"]},
        headers=headers(ip),
        timeout=TIMEOUT,
    )


def lab_1(ip: str) -> None:
    print("\n=== ЛР №1: автентифікація, валідація, SQL-ін'єкції ===")

    weak = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={"username": "ab", "email": "bad", "password": "abc"},
        headers=headers(ip),
        timeout=TIMEOUT,
    )
    body = weak.json()
    detail = body.get("detail", {})
    errors = detail.get("errors", [])
    field_errors = detail.get("field_errors", {})

    check("слабкі дані відхилено (400)", weak.status_code == 400)
    check(
        "повернуто всі помилки одразу",
        len(errors) >= 5,
        f"{len(errors)} повідомлень",
    )
    check(
        "помилки згруповані за полями",
        {"username", "email", "password"} <= set(field_errors),
        str(sorted(field_errors)),
    )
    check(
        "повідомлення локалізовані українською",
        not re.search(r"String should|valid email|at least|Field required", weak.text),
    )
    check(
        "пароль перевірено на складність",
        any("велику літеру" in error for error in errors)
        and any("спеціальний символ" in error for error in errors),
    )

    user = new_user("lab1")
    created = register(ip, user)
    check("коректна реєстрація (201)", created.status_code == 201, created.text[:120])

    signed_in = login(ip, user)
    check(
        "успішний вхід (200)",
        signed_in.status_code == 200 and "access_token" in signed_in.json(),
    )

    sqli = requests.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "username": "admin' OR '1'='1",
            "email": "sqli@example.com",
            "password": "Aa1!aaaa",
        },
        headers=headers(ip),
        timeout=TIMEOUT,
    )
    check(
        "SQL-ін'єкцію заблоковано WAF (403)",
        sqli.status_code == 403 and "WAF Blocked" in sqli.text,
        sqli.text[:120],
    )

    greylist = requests.get(
        f"{BASE_URL}/docs", headers=headers(ip), timeout=TIMEOUT
    )
    check(
        "IP після атаки у Greylist (403)",
        greylist.status_code == 403 and "заблоковано" in greylist.text.lower(),
    )


def lab_2(ip: str) -> None:
    print("\n=== ЛР №2: JWT, захищений профіль, ротація токенів ===")

    user = new_user("lab2")
    check("реєстрація користувача", register(ip, user).status_code == 201)

    signed_in = login(ip, user)
    check("вхід і видача пари токенів", signed_in.status_code == 200)
    tokens = signed_in.json()
    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")
    check("access_token і refresh_token різні", access and refresh and access != refresh)

    profile = requests.get(
        f"{BASE_URL}/api/v1/user/profile",
        headers=headers(ip, access),
        timeout=TIMEOUT,
    )
    check(
        "профіль доступний з access_token",
        profile.status_code == 200
        and profile.json()["user_data"]["username"] == user["username"],
    )

    anonymous = requests.get(
        f"{BASE_URL}/api/v1/user/profile", headers=headers(ip), timeout=TIMEOUT
    )
    check("профіль без токена → 401", anonymous.status_code == 401)

    header, payload, signature = access.split(".")
    forged_payload = payload[:-2] + ("AA" if not payload.endswith("AA") else "BB")
    forged = f"{header}.{forged_payload}.{signature}"
    tampered = requests.get(
        f"{BASE_URL}/api/v1/user/profile",
        headers=headers(ip, forged),
        timeout=TIMEOUT,
    )
    check("підроблений підпис → 401", tampered.status_code == 401)

    rotated = requests.post(
        f"{BASE_URL}/api/v1/auth/refresh",
        json={"refresh_token": refresh},
        headers=headers(ip),
        timeout=TIMEOUT,
    )
    check("ротація refresh-токена (200)", rotated.status_code == 200, rotated.text[:120])
    new_tokens = rotated.json() if rotated.status_code == 200 else {}
    check(
        "видано нову пару токенів",
        new_tokens.get("refresh_token") not in {None, refresh}
        and new_tokens.get("access_token") not in {None, access},
    )

    replay = requests.post(
        f"{BASE_URL}/api/v1/auth/refresh",
        json={"refresh_token": refresh},
        headers=headers(ip),
        timeout=TIMEOUT,
    )
    check(
        "повторне використання refresh → 401 (Replay)",
        replay.status_code == 401 and "replay" in replay.text.lower(),
        replay.text[:120],
    )


def lab_3(ip: str) -> None:
    print("\n=== ЛР №3: заголовки безпеки, cookie, санітизація XSS ===")

    page = requests.get(f"{BASE_URL}/", headers=headers(ip), timeout=TIMEOUT)
    csp = page.headers.get("Content-Security-Policy", "")
    check("CSP забороняє inline-скрипти", "script-src 'self'" in csp)
    check("X-Frame-Options: DENY", page.headers.get("X-Frame-Options") == "DENY")
    check(
        "X-Content-Type-Options: nosniff",
        page.headers.get("X-Content-Type-Options") == "nosniff",
    )
    check("HSTS присутній", "max-age=" in page.headers.get("Strict-Transport-Security", ""))
    check(
        "Referrer-Policy налаштовано",
        page.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin",
    )

    user = new_user("lab3")
    register(ip, user)
    signed_in = login(ip, user)
    check("вхід для перевірки cookie", signed_in.status_code == 200)

    cookie_headers = ""
    raw_headers = getattr(signed_in.raw.headers, "getlist", None)
    if raw_headers:
        cookie_headers = "\n".join(raw_headers("Set-Cookie"))
    else:
        cookie_headers = signed_in.headers.get("Set-Cookie", "")

    access_cookie = next(
        (line for line in cookie_headers.splitlines() if line.startswith("access_token=")),
        "",
    )
    refresh_cookie = next(
        (line for line in cookie_headers.splitlines() if line.startswith("refresh_token=")),
        "",
    )
    check(
        "access_token cookie: HttpOnly",
        "HttpOnly" in access_cookie,
        access_cookie[:120],
    )
    check(
        "refresh_token cookie: HttpOnly",
        "HttpOnly" in refresh_cookie,
        refresh_cookie[:120],
    )
    check(
        "cookie має SameSite=strict",
        "samesite=strict" in access_cookie.lower()
        and "samesite=strict" in refresh_cookie.lower(),
    )

    access = signed_in.json()["access_token"]
    upload = requests.post(
        f"{BASE_URL}/api/v1/documents/upload",
        files={"file": ("lab3.txt", b"laboratory 3 content", "text/plain")},
        headers=headers(ip, access),
        timeout=TIMEOUT,
    )
    check("завантаження документа для коментаря", upload.status_code == 201, upload.text[:120])
    document_id = upload.json().get("document_id", "")

    xss = "<script>alert('XSS')</script><img src=x onerror=alert(1)>"
    comment = requests.post(
        f"{BASE_URL}/api/v1/documents/{document_id}/comments",
        json={"title": "XSS <b>test</b>", "comment": xss},
        headers=headers(ip, access),
        timeout=TIMEOUT,
    )
    check("XSS-коментар прийнято (201)", comment.status_code == 201, comment.text[:120])
    sanitized = comment.json().get("sanitized_comment", "") if comment.status_code == 201 else ""
    check(
        "XSS-теги вирізано санітизатором",
        "<script" not in sanitized.lower() and "onerror" not in sanitized.lower(),
        sanitized[:120],
    )

    stored = requests.get(
        f"{BASE_URL}/api/v1/documents/{document_id}/comments",
        headers=headers(ip, access),
        timeout=TIMEOUT,
    )
    stored_text = stored.text.lower()
    check(
        "у сховищі немає виконуваного XSS",
        stored.status_code == 200
        and "<script" not in stored_text
        and "onerror" not in stored_text,
    )


def lab_4(ip_rate: str, ip_waf: str) -> None:
    print("\n=== ЛР №4: Rate Limiting, WAF, Greylist ===")

    statuses: list[int] = []
    retry_after = ""
    for _ in range(10):
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
            headers=headers(ip_rate),
            timeout=TIMEOUT,
        )
        statuses.append(response.status_code)
        if response.status_code == 429 and not retry_after:
            retry_after = response.headers.get("Retry-After", "")

    check(
        "перші 5 спроб дійшли до бізнес-логіки (401)",
        statuses[:5] == [401] * 5,
        str(statuses),
    )
    check("після ліміту → 429 Too Many Requests", 429 in statuses, str(statuses))
    check("заголовок Retry-After присутній", bool(retry_after), retry_after)

    traversal = requests.get(
        f"{BASE_URL}/api/v1/user/profile?file=../../etc/passwd",
        headers=headers(ip_waf),
        timeout=TIMEOUT,
    )
    check(
        "Path Traversal заблоковано (403)",
        traversal.status_code == 403 and "WAF Blocked" in traversal.text,
        traversal.text[:120],
    )

    greylist = requests.get(
        f"{BASE_URL}/docs", headers=headers(ip_waf), timeout=TIMEOUT
    )
    check(
        "Greylist блокує наступні запити (403)",
        greylist.status_code == 403 and "заблоковано" in greylist.text.lower(),
    )


def main() -> int:
    print(f"Secure DocVault: перевірка ЛР №1–4 — {BASE_URL}")
    lab_1("10.10.0.11")
    lab_2("10.10.0.12")
    lab_3("10.10.0.13")
    lab_4("10.10.0.14", "10.10.0.15")

    passed = sum(1 for _, ok, _ in results if ok)
    failed = len(results) - passed
    print(f"\nПідсумок: {passed} успішно, {failed} з помилками.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
