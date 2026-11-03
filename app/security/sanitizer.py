from __future__ import annotations

import re

import bleach

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_LENGTH = 4000


def sanitize_user_input(text: str | None, max_length: int = _MAX_LENGTH) -> str:
    if not text:
        return ""

    cleaned = _CONTROL_CHARS.sub(" ", text)
    cleaned = bleach.clean(
        cleaned,
        tags=[],
        attributes={},
        protocols=[],
        strip=True,
    )
    cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    return cleaned.strip()[:max_length]


def sanitize_multiline(text: str | None, max_length: int = _MAX_LENGTH) -> str:
    if not text:
        return ""

    cleaned = _CONTROL_CHARS.sub("", text)
    cleaned = bleach.clean(cleaned, tags=[], attributes={}, protocols=[], strip=True)
    return cleaned.strip()[:max_length]
