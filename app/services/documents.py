from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from fastapi import UploadFile

import config as settings
from app.logging_config import audit
from app.repositories.comments import CommentRepository
from app.repositories.documents import DocumentRepository
from app.security.filenames import content_disposition, sanitize_filename
from app.security.file_types import validate_upload
from app.security.sanitizer import sanitize_multiline, sanitize_user_input
from app.security.vault import decrypt_from_file, encrypt_to_file, make_aad
from app.services import signing as signing_service
from app.services.errors import (
    AppError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalError,
    NotFoundError,
    PayloadTooLargeError,
)

logger = logging.getLogger("services.documents")


@dataclass(frozen=True)
class DownloadResult:
    content: bytes
    media_type: str
    headers: dict[str, str]


def _serialize(document: dict) -> dict:
    return {
        "document_id": document["id"],
        "original_filename": document["original_filename"],
        "content_type": document.get("content_type"),
        "size_bytes": document.get("original_size") or document.get("file_size"),
        "encrypted_size_bytes": document["file_size"],
        "sha256": document.get("sha256"),
        "owner_id": document["owner_id"],
        "created_at": document.get("created_at"),
        "signature": signing_service.get_signature_info(document["id"]),
    }


def _document_for_user(doc_id: str, current_user: dict) -> dict:
    document = DocumentRepository.get(doc_id)
    if not document:
        raise NotFoundError("Документ не знайдено")

    is_admin = current_user.get("role") == "admin"
    if document["owner_id"] != current_user["user_id"] and not is_admin:
        audit(
            "document_access_denied",
            user=current_user["username"],
            doc=doc_id,
        )
        raise ForbiddenError("Немає прав доступу до даного документа")
    return document


def _stored_file_path(document: dict) -> Path:
    stored = Path(document["stored_filename"]).name
    return settings.UPLOAD_DIR / stored


def list_documents(current_user: dict) -> list[dict]:
    documents = DocumentRepository.list_for_owner(
        current_user["user_id"], is_admin=current_user.get("role") == "admin"
    )
    return [_serialize(document) for document in documents]


def get_document(doc_id: str, current_user: dict) -> dict:
    return _serialize(_document_for_user(doc_id, current_user))


async def upload(
    file: UploadFile,
    declared_length: str | None,
    current_user: dict,
) -> dict:
    if declared_length:
        try:
            if int(declared_length) > settings.MAX_UPLOAD_SIZE + 64 * 1024:
                raise PayloadTooLargeError(
                    f"Файл перевищує ліміт {settings.MAX_UPLOAD_SIZE} байт"
                )
        except ValueError:
            pass

    filename = sanitize_filename(file.filename)

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(settings.UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.MAX_UPLOAD_SIZE:
            raise PayloadTooLargeError(
                f"Файл перевищує ліміт {settings.MAX_UPLOAD_SIZE} байт"
            )
        chunks.append(chunk)

    if total == 0:
        raise BadRequestError("Файл порожній")

    raw_content = b"".join(chunks)

    is_valid, error_message = validate_upload(
        filename, raw_content[:4096], settings.ALLOWED_EXTENSIONS
    )
    if not is_valid:
        audit(
            "upload_rejected",
            user=current_user["username"],
            filename=filename,
            reason=error_message,
        )
        raise BadRequestError(error_message)

    doc_id = str(uuid.uuid4())
    stored_filename = f"{doc_id}.enc"
    destination = settings.UPLOAD_DIR / stored_filename
    associated_data = make_aad(doc_id, current_user["user_id"])

    try:
        encrypted_size = encrypt_to_file(raw_content, destination, associated_data)
    except OSError as exc:
        logger.exception("Не вдалося записати шифроконтейнер %s", destination)
        raise InternalError("Не вдалося зберегти файл") from exc

    digest = hashlib.sha256(raw_content).hexdigest()
    saved = DocumentRepository.save(
        doc_id=doc_id,
        original_filename=filename,
        stored_filename=stored_filename,
        owner_id=current_user["user_id"],
        file_size=encrypted_size,
        content_type=file.content_type,
        original_size=total,
        sha256=digest,
    )

    if not saved:
        destination.unlink(missing_ok=True)
        raise InternalError("Помилка збереження метаданих файлу в БД")

    try:
        signature = signing_service.sign_content_for_user(
            raw_content, current_user["user_id"]
        )
        signing_service.store_document_signature(
            doc_id, current_user["user_id"], signature
        )
    except AppError:
        DocumentRepository.delete(doc_id)
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        DocumentRepository.delete(doc_id)
        destination.unlink(missing_ok=True)
        logger.exception("Не вдалося підписати документ %s", doc_id)
        raise InternalError("Не вдалося створити електронний підпис") from exc

    audit(
        "document_uploaded",
        user=current_user["username"],
        doc=doc_id,
        filename=filename,
        size=total,
    )

    return {
        "status": "success",
        "document_id": doc_id,
        "original_filename": filename,
        "size_bytes": total,
        "encrypted_size_bytes": encrypted_size,
        "sha256": digest,
        "signature": signing_service.get_signature_info(doc_id),
        "message": "Файл успішно зашифровано, підписано та збережено в сховищі",
    }


def download(doc_id: str, current_user: dict) -> DownloadResult:
    document = _document_for_user(doc_id, current_user)
    file_path = _stored_file_path(document)

    if not file_path.exists():
        raise NotFoundError("Зашифрований файл відсутній на диску")

    associated_data = make_aad(document["id"], document["owner_id"])
    try:
        plaintext = decrypt_from_file(
            file_path, associated_data, settings.MAX_UPLOAD_SIZE
        )
    except InvalidTag as exc:
        logger.error(
            "Цілісність порушено: doc=%s user=%s", doc_id, current_user["username"]
        )
        audit(
            "integrity_violation",
            doc=doc_id,
            user=current_user["username"],
        )
        raise ConflictError(
            "КРИТИЧНА ПОМИЛКА БЕЗПЕКИ: файл на диску фальсифіковано "
            "або пошкоджено (InvalidTag)."
        ) from exc
    except ValueError as exc:
        raise BadRequestError(f"Помилка дешифрування: {exc}") from exc

    expected_hash = document.get("sha256")
    if expected_hash and hashlib.sha256(plaintext).hexdigest() != expected_hash:
        logger.error("SHA-256 не збігається для doc=%s", doc_id)
        raise ConflictError("Перевірка цілісності SHA-256 не пройдена.")

    signature = signing_service.verify_document(doc_id, plaintext)
    if signature["status"] == "invalid":
        raise ConflictError(
            "Цифровий підпис документа недійсний: підпис не відповідає "
            "вмісту або відсутній відкритий ключ підписанта."
        )

    headers = {
        "Content-Disposition": content_disposition(document["original_filename"]),
        "X-Content-SHA256": expected_hash or "",
        "X-Signature-Status": (
            "Signed & Verified"
            if signature["status"] == "verified"
            else "Unsigned"
        ),
    }
    if signature["status"] == "verified":
        headers.update(
            {
                "X-Signature-Algorithm": signature["algorithm"],
                "X-Signature-Fingerprint": signature["fingerprint"],
                "X-Signer": signature.get("signer") or "",
                "X-Signed-At": signature.get("signed_at") or "",
            }
        )

    audit("document_downloaded", doc=doc_id, user=current_user["username"])

    return DownloadResult(
        content=plaintext,
        media_type=document.get("content_type") or "application/octet-stream",
        headers=headers,
    )


def delete(doc_id: str, current_user: dict) -> None:
    document = _document_for_user(doc_id, current_user)
    _stored_file_path(document).unlink(missing_ok=True)

    if not DocumentRepository.delete(doc_id):
        raise InternalError("Не вдалося видалити документ")

    audit("document_deleted", doc=doc_id, user=current_user["username"])


def add_comment(
    doc_id: str,
    title: str,
    comment: str,
    current_user: dict,
) -> dict:
    _document_for_user(doc_id, current_user)

    clean_title = sanitize_user_input(title, max_length=200)
    clean_comment = sanitize_multiline(comment, max_length=4000)

    if not clean_title or not clean_comment:
        raise BadRequestError("Порожній заголовок або коментар")

    stored = CommentRepository.add(
        doc_id, current_user["user_id"], clean_title, clean_comment
    )
    audit("comment_added", doc=doc_id, user=current_user["username"])

    return {
        "comment": stored,
        "original_comment": comment,
        "sanitized_comment": clean_comment,
    }


def list_comments(doc_id: str, current_user: dict) -> list[dict]:
    _document_for_user(doc_id, current_user)
    return CommentRepository.list_for_document(doc_id)
