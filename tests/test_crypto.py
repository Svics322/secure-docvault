from __future__ import annotations

import pytest
from cryptography.exceptions import InvalidTag

import config
from app.security import secrets as secrets_manager
from app.security.vault import (
    decrypt_file_content,
    encrypt_file_content,
    make_aad,
)


def test_integrity_test_detects_one_bit_change():
    original = b"CONFIDENTIAL FINANCIAL REPORT - SECURE DOCVAULT 2026"
    blob = encrypt_file_content(original)

    assert decrypt_file_content(blob) == original

    corrupted = bytearray(blob)
    corrupted[20] ^= 0xFF

    with pytest.raises(InvalidTag):
        decrypt_file_content(bytes(corrupted))


def test_nonce_is_unique_per_operation():
    first = encrypt_file_content(b"same payload")
    second = encrypt_file_content(b"same payload")

    assert first[:12] != second[:12]
    assert first != second


def test_aad_binding_prevents_cross_document_swap():
    doc_a = make_aad("doc-a", 1)
    doc_b = make_aad("doc-b", 1)

    blob = encrypt_file_content(b"document A content", associated_data=doc_a)

    assert decrypt_file_content(blob, associated_data=doc_a) == b"document A content"
    with pytest.raises(InvalidTag):
        decrypt_file_content(blob, associated_data=doc_b)


def test_container_format_lengths():
    payload = b"abc"
    blob = encrypt_file_content(payload)
    assert len(blob) == 12 + len(payload) + 16


def test_truncated_container_rejected():
    with pytest.raises(ValueError):
        decrypt_file_content(b"short")


def test_leaked_jwt_key_is_refused():
    leaked = next(iter(config.LEAKED_JWT_SECRETS))
    with pytest.raises(secrets_manager.SecretError):
        secrets_manager._validate(
            "JWT_SECRET_KEY", leaked, hex_encoded=False, min_bytes=32
        )


def test_short_secret_is_refused():
    with pytest.raises(secrets_manager.SecretError):
        secrets_manager._validate(
            "JWT_SECRET_KEY", "too-short", hex_encoded=False, min_bytes=32
        )


def test_invalid_hex_key_is_refused():
    with pytest.raises(secrets_manager.SecretError):
        secrets_manager._validate(
            "FILE_ENCRYPTION_KEY", "zz" * 32, hex_encoded=True, min_bytes=32
        )
