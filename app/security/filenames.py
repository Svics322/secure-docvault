from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_UNSAFE_ASCII = re.compile(r"[^A-Za-z0-9._ -]")
_FALLBACK_NAME = "document"

MAX_FILENAME_LENGTH = 120


def sanitize_filename(raw_name: str | None, max_length: int = MAX_FILENAME_LENGTH) -> str:
    if not raw_name:
        return _FALLBACK_NAME

    name = raw_name.replace("\\", "/").split("/")[-1]
    name = _CONTROL_CHARS.sub("", name)
    name = name.replace("\u202a", "").replace("\u202b", "").replace("\u202c", "")
    name = name.replace("\u202d", "").replace("\u202e", "").replace("\u2066", "")
    name = name.replace("\u2067", "").replace("\u2068", "").replace("\u2069", "")

    name = name.replace('"', "'")
    name = name.strip().strip(".").strip()
    name = re.sub(r"\s+", " ", name)

    if not name:
        return _FALLBACK_NAME

    if len(name) > max_length:
        stem, dot, extension = name.rpartition(".")
        if dot and len(extension) <= 10:
            keep = max_length - len(extension) - 1
            name = f"{stem[:keep]}.{extension}"
        else:
            name = name[:max_length]

    return name or _FALLBACK_NAME


def ascii_fallback(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", filename)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    ascii_name = _UNSAFE_ASCII.sub("_", ascii_name).strip(" ._")
    return ascii_name[:MAX_FILENAME_LENGTH] or _FALLBACK_NAME


def content_disposition(filename: str, *, disposition: str = "attachment") -> str:
    safe_name = sanitize_filename(filename)
    fallback = ascii_fallback(safe_name)
    encoded = quote(safe_name, safe="")
    return f'{disposition}; filename="{fallback}"; filename*=UTF-8\'\'{encoded}'
