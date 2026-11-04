from __future__ import annotations

import base64
import logging

from app.logging_config import audit
from app.repositories.signing import SignatureRepository, SigningKeyRepository
from app.repositories.users import UserRepository
from app.security import signatures as crypto
from app.services.errors import InternalError, ValidationError

logger = logging.getLogger("services.signing")

MIN_PASSPHRASE_LENGTH = 8
MAX_PASSPHRASE_LENGTH = 128


def _key_info(row: dict) -> dict:
    return {
        "algorithm": row["algorithm"],
        "fingerprint": row["key_fingerprint"],
        "public_key_pem": row["public_key_pem"],
        "created_at": row.get("created_at"),
    }


def ensure_user_key(user_id: int) -> dict:
    existing = SigningKeyRepository.get(user_id)
    if existing:
        return existing

    private_key, public_key = crypto.generate_keypair()
    public_pem = crypto.serialize_public_key(public_key)
    private_pem = crypto.serialize_private_key(private_key)
    encrypted_private = crypto.encrypt_private_key_pem(private_pem)
    fingerprint = crypto.public_key_fingerprint(public_key)

    saved = SigningKeyRepository.save(
        user_id=user_id,
        public_key_pem=public_pem,
        private_key_encrypted=encrypted_private,
        key_fingerprint=fingerprint,
        algorithm=crypto.ALGORITHM,
    )
    if not saved:
        # Можлива гонка двох перших запитів: якщо інший процес уже створив
        # ключ, використовуємо його.
        existing = SigningKeyRepository.get(user_id)
        if existing:
            return existing
        raise InternalError("Не вдалося зберегти ключі електронного підпису")

    audit(
        "signing_key_generated",
        user_id=user_id,
        algorithm=crypto.ALGORITHM,
        fingerprint=fingerprint,
    )
    created = SigningKeyRepository.get(user_id)
    if not created:
        raise InternalError("Не вдалося прочитати створені ключі підпису")
    return created


def find_key_info(user_id: int) -> dict | None:
    row = SigningKeyRepository.get(user_id)
    return _key_info(row) if row else None


def get_key_info(user_id: int) -> dict:
    return _key_info(ensure_user_key(user_id))


def get_public_key_pem(user_id: int) -> str:
    return ensure_user_key(user_id)["public_key_pem"]


def _validate_passphrase(passphrase: str) -> None:
    errors: list[str] = []
    value = passphrase or ""

    if not value.strip():
        errors.append("Парольна фраза є обов'язковою")
    elif len(value) < MIN_PASSPHRASE_LENGTH:
        errors.append(
            f"Парольна фраза має містити щонайменше "
            f"{MIN_PASSPHRASE_LENGTH} символів"
        )
    if len(value) > MAX_PASSPHRASE_LENGTH:
        errors.append(
            f"Парольна фраза не повинна перевищувати "
            f"{MAX_PASSPHRASE_LENGTH} символів"
        )

    if errors:
        raise ValidationError(errors, field_errors={"passphrase": errors})


def export_private_key(user_id: int, passphrase: str) -> str:
    _validate_passphrase(passphrase)
    key = ensure_user_key(user_id)

    try:
        private_pem = crypto.decrypt_private_key_pem(key["private_key_encrypted"])
        private_key = crypto.load_private_key(private_pem)
        exported = crypto.serialize_private_key(private_key, passphrase)
    except ValueError as exc:
        logger.exception("Не вдалося експортувати приватний ключ user_id=%s", user_id)
        raise InternalError("Не вдалося експортувати приватний ключ") from exc

    audit(
        "signing_key_exported",
        user_id=user_id,
        fingerprint=key["key_fingerprint"],
    )
    return exported


def sign_content_for_user(content: bytes, user_id: int) -> dict:
    key = ensure_user_key(user_id)
    try:
        private_pem = crypto.decrypt_private_key_pem(key["private_key_encrypted"])
        private_key = crypto.load_private_key(private_pem)
        signature = crypto.sign_content(content, private_key)
        public_key = crypto.load_public_key(key["public_key_pem"])
    except ValueError as exc:
        logger.exception("Не вдалося підписати документ user_id=%s", user_id)
        raise InternalError("Не вдалося створити електронний підпис") from exc

    if not crypto.verify_content(content, signature, public_key):
        raise InternalError("Створений електронний підпис не пройшов перевірку")

    return {
        "signature_b64": base64.b64encode(signature).decode("ascii"),
        "algorithm": key["algorithm"],
        "fingerprint": key["key_fingerprint"],
    }


def store_document_signature(
    document_id: str, signer_id: int, signature: dict
) -> None:
    saved = SignatureRepository.save(
        document_id=document_id,
        signer_id=signer_id,
        algorithm=signature["algorithm"],
        signature_b64=signature["signature_b64"],
        public_key_fingerprint=signature["fingerprint"],
    )
    if not saved:
        raise InternalError("Не вдалося зберегти електронний підпис документа")

    audit(
        "document_signed",
        doc=document_id,
        user_id=signer_id,
        algorithm=signature["algorithm"],
        fingerprint=signature["fingerprint"],
    )


def get_signature_info(document_id: str) -> dict:
    signature = SignatureRepository.get(document_id)
    if not signature:
        return {"status": "unsigned"}

    signer = UserRepository.get_by_id(signature["signer_id"])
    return {
        "status": "signed",
        "algorithm": signature["algorithm"],
        "signed_at": signature.get("signed_at"),
        "signer": signer["username"] if signer else None,
        "signer_id": signature["signer_id"],
        "fingerprint": signature["public_key_fingerprint"],
    }


def verify_document(document_id: str, content: bytes) -> dict:
    signature = SignatureRepository.get(document_id)
    if not signature:
        return {"status": "unsigned"}

    key = SigningKeyRepository.get(signature["signer_id"])
    if not key:
        audit("document_signature_invalid", doc=document_id, reason="key_missing")
        return {"status": "invalid", "reason": "key_missing"}

    try:
        raw_signature = base64.b64decode(
            signature["signature_b64"].encode("ascii"), validate=True
        )
        public_key = crypto.load_public_key(key["public_key_pem"])
        valid = crypto.verify_content(content, raw_signature, public_key)
    except (ValueError, TypeError):
        valid = False

    if not valid:
        audit("document_signature_invalid", doc=document_id, reason="bad_signature")
        return {"status": "invalid", "reason": "bad_signature"}

    signer = UserRepository.get_by_id(signature["signer_id"])
    audit(
        "document_signature_verified",
        doc=document_id,
        user_id=signature["signer_id"],
        fingerprint=signature["public_key_fingerprint"],
    )
    return {
        "status": "verified",
        "algorithm": signature["algorithm"],
        "signed_at": signature.get("signed_at"),
        "signer": signer["username"] if signer else None,
        "signer_id": signature["signer_id"],
        "fingerprint": signature["public_key_fingerprint"],
    }
