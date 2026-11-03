from __future__ import annotations

import logging
from pathlib import PurePath

logger = logging.getLogger("file_types")

MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    ".docx": (b"PK\x03\x04",),
    ".xlsx": (b"PK\x03\x04",),
    ".pptx": (b"PK\x03\x04",),
}

TEXT_EXTENSIONS = {".txt", ".csv", ".md", ".log"}

_HEAD_BYTES = 4096


def get_extension(filename: str) -> str:
    return PurePath(filename).suffix.lower()


def _looks_like_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        head.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def validate_upload(
    filename: str,
    head: bytes,
    allowed_extensions: set[str],
) -> tuple[bool, str]:
    extension = get_extension(filename)
    normalized_allowed = {
        ext if ext.startswith(".") else f".{ext}" for ext in allowed_extensions
    }

    if not extension:
        return False, "Файл повинен мати розширення (наприклад, .pdf або .txt)."

    if extension not in normalized_allowed:
        allowed_text = ", ".join(sorted(normalized_allowed))
        return False, f"Тип файлу '{extension}' не дозволено. Дозволені: {allowed_text}."

    sample = head[:_HEAD_BYTES]

    if extension in TEXT_EXTENSIONS:
        if not _looks_like_text(sample):
            return (
                False,
                "Текстовий файл містить бінарні дані або інше кодування "
                "(очікується UTF-8).",
            )
        return True, ""

    signatures = MAGIC_SIGNATURES.get(extension)
    if signatures is None:
        logger.warning("Немає сигнатури для розширення %s", extension)
        return True, ""

    if not sample:
        return False, "Файл порожній."

    if not any(sample.startswith(signature) for signature in signatures):
        return False, (
            f"Вміст файлу не відповідає розширенню '{extension}' "
            f"(перевірка магічних байтів не пройдена)."
        )

    return True, ""
