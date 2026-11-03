from __future__ import annotations

import logging
import re
from urllib.parse import unquote_plus

logger = logging.getLogger("middleware.waf")

URL = "url"
BODY = "body"

HIGH_CONFIDENCE_SIGNATURES: list[tuple[str, str, str]] = [
    (r"\.\.[\\/]", "Path Traversal Attack", URL + BODY),
    (r"(?i)\bunion\s+(?:all\s+)?select\b", "SQL Injection Signature", URL + BODY),
    (
        r"(?i)\b(?:insert\s+into|drop\s+table|delete\s+from|truncate\s+table)\b",
        "SQL Injection Signature",
        URL + BODY,
    ),
    (r"(?i)'\s*(?:or|and)\s*'?1'?\s*=\s*'?1", "SQL Injection Signature", URL + BODY),
    (r"(?i)\bexec(?:ute)?\s+xp_", "SQL Injection Signature", URL + BODY),
    (
        r"(?i)(<script|javascript\s*:|onerror\s*=|onload\s*=|"
        r"<iframe|<svg)",
        "XSS Attack Signature",
        URL,
    ),
    (
        r"(?i)(\|\s*(?:sh|bash)\b|cmd\.exe|/bin/(?:sh|bash)\b|system\s*\()",
        "Command Injection Signature",
        URL + BODY,
    ),
]

LOW_CONFIDENCE_SIGNATURES: list[tuple[str, str, str]] = [
    (r"(?i)(?:^|[\s\"'();,])--(?:$|[\s\"'();,])", "SQL Comment Signature", URL + BODY),
    (r"/\*", "SQL Comment Signature", URL + BODY),
]

_COMPILED_HIGH = [
    (re.compile(pattern), description, scope)
    for pattern, description, scope in HIGH_CONFIDENCE_SIGNATURES
]
_COMPILED_LOW = [
    (re.compile(pattern), description, scope)
    for pattern, description, scope in LOW_CONFIDENCE_SIGNATURES
]

_SKIP_BODY_TYPES = (
    "multipart/form-data",
    "application/octet-stream",
    "application/pdf",
    "image/",
    "video/",
    "audio/",
)


def _normalize(text: str) -> str:
    if not text:
        return ""
    decoded = text
    for _ in range(2):
        try:
            next_value = unquote_plus(decoded)
        except (UnicodeDecodeError, ValueError):
            break
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def should_inspect_body(content_type: str | None) -> bool:
    if not content_type:
        return False
    lowered = content_type.lower()
    return not any(skip in lowered for skip in _SKIP_BODY_TYPES)


def multipart_text_fields(body_text: str, limit: int = 64 * 1024) -> str:
    if not body_text:
        return ""

    fields: list[str] = []
    for line in body_text[:limit].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("--") and len(stripped) < 80:
            continue
        if any(ord(char) < 9 for char in stripped):
            continue
        fields.append(stripped)
    return "\n".join(fields)


def _match(text: str, *targets: str) -> tuple[bool, str, str]:
    if not text:
        return False, "", ""

    for pattern, description, scope in _COMPILED_HIGH:
        if any(target in scope for target in targets) and pattern.search(text):
            return True, description, "high"

    for pattern, description, scope in _COMPILED_LOW:
        if any(target in scope for target in targets) and pattern.search(text):
            return True, description, "low"

    return False, "", ""


def inspect_payload(content: str) -> tuple[bool, str]:
    is_attack, description, _severity = _match(_normalize(content), URL, BODY)
    return is_attack, description


def inspect_request_data(
    url_path: str,
    query_params: str,
    body_text: str,
    client_ip: str,
    content_type: str | None = None,
) -> tuple[bool, str, str]:
    url_part = _normalize(url_path)
    if query_params:
        url_part += "\n" + _normalize(query_params)

    is_attack, description, severity = _match(url_part, URL)

    if not is_attack and body_text:
        if content_type and "multipart/form-data" in content_type.lower():
            body_part = multipart_text_fields(body_text)
        elif should_inspect_body(content_type):
            body_part = _normalize(body_text)
        else:
            body_part = ""
        is_attack, description, severity = _match(body_part, BODY)
    if is_attack:
        logger.error(
            "[WAF BLOCK] IP: %s | Attack: '%s' (%s) | Path: %s",
            client_ip,
            description,
            severity,
            url_path,
        )

    return is_attack, description, severity
