from __future__ import annotations

import logging
import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.security.secrets import load_secret

logger = logging.getLogger("security.vault")

NONCE_SIZE = 12
TAG_SIZE = 16
MIN_CONTAINER_SIZE = NONCE_SIZE + TAG_SIZE
CHUNK_SIZE = 1024 * 1024
LEGACY_AAD = b"docvault"


def _load_key(name: str) -> bytes:
    return bytes.fromhex(load_secret(name, nbytes=32))


def _load_old_keys() -> list[bytes]:
    raw = os.getenv("FILE_ENCRYPTION_KEY_OLD", "").strip()
    keys: list[bytes] = []
    for candidate in raw.split(","):
        candidate = candidate.strip()
        if len(candidate) == 64:
            try:
                keys.append(bytes.fromhex(candidate))
            except ValueError:
                logger.error(
                    "FILE_ENCRYPTION_KEY_OLD містить некоректний Hex-ключ — пропущено"
                )
    return keys


MASTER_KEY = _load_key("FILE_ENCRYPTION_KEY")
ALL_KEYS: tuple[bytes, ...] = (MASTER_KEY, *_load_old_keys())


def make_aad(document_id: str, owner_id: int | str) -> bytes:
    return f"docvault|v1|{document_id}|{owner_id}".encode("utf-8")


def encrypt_file_content(data: bytes, associated_data: bytes = LEGACY_AAD) -> bytes:
    nonce = os.urandom(NONCE_SIZE)
    encrypted = AESGCM(MASTER_KEY).encrypt(nonce, data, associated_data)
    return nonce + encrypted


def decrypt_file_content(payload: bytes, associated_data: bytes = LEGACY_AAD) -> bytes:
    if len(payload) < MIN_CONTAINER_SIZE:
        raise ValueError(
            f"Пошкоджений або занадто короткий шифроконтейнер "
            f"(мінімум {MIN_CONTAINER_SIZE} байт)"
        )

    nonce = payload[:NONCE_SIZE]
    ciphertext_with_tag = payload[NONCE_SIZE:]

    last_error: InvalidTag | None = None
    for key in ALL_KEYS:
        try:
            return AESGCM(key).decrypt(nonce, ciphertext_with_tag, associated_data)
        except InvalidTag as exc:
            last_error = exc

    raise last_error if last_error else InvalidTag("Не вдалося перевірити тег")


def encrypt_to_file(data: bytes, destination: Path, associated_data: bytes) -> int:
    nonce = os.urandom(NONCE_SIZE)
    encryptor = Cipher(algorithms.AES(MASTER_KEY), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(associated_data)

    with open(destination, "wb") as handle:
        handle.write(nonce)
        for offset in range(0, len(data), CHUNK_SIZE):
            handle.write(encryptor.update(data[offset : offset + CHUNK_SIZE]))
        encryptor.finalize()
        handle.write(encryptor.tag)
        handle.flush()
        os.fsync(handle.fileno())

    return destination.stat().st_size


def decrypt_from_file(source: Path, associated_data: bytes, max_size: int) -> bytes:
    size = source.stat().st_size
    if size < MIN_CONTAINER_SIZE:
        raise ValueError("Пошкоджений або занадто короткий шифроконтейнер")

    plaintext_size = size - MIN_CONTAINER_SIZE
    if plaintext_size > max_size:
        raise ValueError(
            f"Розшифрований файл перевищує ліміт ({plaintext_size} > {max_size} байт)"
        )

    with open(source, "rb") as handle:
        nonce = handle.read(NONCE_SIZE)
        handle.seek(size - TAG_SIZE)
        tag = handle.read(TAG_SIZE)
        handle.seek(NONCE_SIZE)

        last_error: InvalidTag | None = None
        for key in ALL_KEYS:
            handle.seek(NONCE_SIZE)
            try:
                decryptor = Cipher(
                    algorithms.AES(key), modes.GCM(nonce, tag)
                ).decryptor()
                decryptor.authenticate_additional_data(associated_data)
                output = bytearray()
                remaining = plaintext_size
                while remaining > 0:
                    chunk = handle.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    output += decryptor.update(chunk)
                output += decryptor.finalize()
                return bytes(output)
            except InvalidTag as exc:
                last_error = exc

    raise last_error if last_error else InvalidTag("Не вдалося перевірити тег")
