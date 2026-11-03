from __future__ import annotations

import logging
import os
import re
import secrets
import time

from config import ENV_PATH, LEAKED_JWT_SECRETS

logger = logging.getLogger("secrets")

_LOCK_TIMEOUT_SECONDS = 10.0
_LOCK_RETRY_SECONDS = 0.05
_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class SecretError(RuntimeError):
    pass


def _read_env_file(name: str) -> str | None:
    if not ENV_PATH.exists():
        return None
    try:
        content = ENV_PATH.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - залежить від ФС
        raise SecretError(f"Не вдалося прочитати {ENV_PATH}: {exc}") from exc

    value: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw = stripped.split("=", 1)
        if key.strip() == name:
            value = raw.strip().strip('"').strip("'")
    return value or None


def _append_env_atomically(name: str, value: str) -> str:
    lock_path = ENV_PATH.with_name(ENV_PATH.name + ".lock")
    deadline = time.monotonic() + _LOCK_TIMEOUT_SECONDS
    fd: int | None = None

    while fd is None:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() > deadline:
                raise SecretError(
                    f"Файл блокування {lock_path} не звільнився за "
                    f"{_LOCK_TIMEOUT_SECONDS:.0f} с. Перевірте, чи не завис інший процес."
                ) from None
            time.sleep(_LOCK_RETRY_SECONDS)

    try:
        os.close(fd)
        fd = None

        existing = _read_env_file(name)
        if existing:
            return existing

        content = ""
        if ENV_PATH.exists():
            content = ENV_PATH.read_text(encoding="utf-8")
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{name}={value}\n"

        with open(ENV_PATH, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return value
    except OSError as exc:
        raise SecretError(
            f"Не вдалося зберегти {name} у {ENV_PATH}: {exc}. "
            f"Задайте {name} через змінну оточення або зробіть файл доступним для запису."
        ) from exc
    finally:
        if fd is not None:  # pragma: no cover - захист від часткового відкриття
            os.close(fd)
        try:
            lock_path.unlink()
        except OSError:
            pass


def _validate(name: str, value: str, *, hex_encoded: bool, min_bytes: int) -> None:
    if name == "JWT_SECRET_KEY" and value.strip().lower() in LEAKED_JWT_SECRETS:
        raise SecretError(
            "JWT_SECRET_KEY збігається з ключем, який уже опубліковано в репозиторії. "
            "Згенеруйте новий: python -c \"import secrets; print(secrets.token_hex(32))\" "
            "і запишіть його у .env."
        )

    if hex_encoded:
        if not _HEX64.match(value):
            raise SecretError(
                f"{name} повинен містити рівно 64 Hex-символи (32 байти), "
                f"а містить {len(value)} символів."
            )
        return

    if len(value.encode("utf-8")) < min_bytes:
        raise SecretError(
            f"{name} занадто короткий: потрібно щонайменше {min_bytes} байт ентропії."
        )


def load_secret(
    name: str,
    *,
    nbytes: int = 32,
    hex_encoded: bool = True,
    min_bytes: int = 32,
    auto_generate: bool = True,
) -> str:
    value = (os.getenv(name) or "").strip()
    source = "environment"

    if not value:
        file_value = _read_env_file(name)
        if file_value:
            value = file_value
            source = str(ENV_PATH)

    if not value:
        if not auto_generate:
            raise SecretError(f"{name} не заданий, а автоматична генерація вимкнена.")

        generated = secrets.token_hex(nbytes)
        value = _append_env_atomically(name, generated)
        source = f"{ENV_PATH} (згенеровано)"
        logger.warning("[SECURITY] %s був відсутній — згенеровано новий ключ.", name)

    _validate(name, value, hex_encoded=hex_encoded, min_bytes=min_bytes)
    os.environ[name] = value

    if source != "environment":
        logger.info("[SECURITY] %s завантажено з %s", name, source)

    return value


def key_fingerprint(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
