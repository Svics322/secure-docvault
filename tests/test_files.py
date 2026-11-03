from __future__ import annotations

import shutil

import pytest

import api
import config as settings
from app.repositories.documents import DocumentRepository


def upload(client, headers, filename, content, content_type="text/plain"):
    return client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (filename, content, content_type)},
    )


def test_upload_without_file_has_friendly_message(client, user_factory):
    user = user_factory()
    response = client.post(
        "/api/v1/documents/upload",
        headers=user["headers"],
        data={},
    )
    assert response.status_code == 400
    assert "Оберіть файл для завантаження" in response.text
    assert "Поле «Файл»" not in response.text


def test_upload_download_roundtrip(client, user_factory):
    user = user_factory()
    payload = b"CONFIDENTIAL: payload for roundtrip test"

    created = upload(client, user["headers"], "report.txt", payload)
    assert created.status_code == 201, created.text
    doc_id = created.json()["document_id"]

    downloaded = client.get(
        f"/api/v1/documents/{doc_id}/download", headers=user["headers"]
    )
    assert downloaded.status_code == 200
    assert downloaded.content == payload


def test_plaintext_not_stored_on_disk(client, user_factory):
    user = user_factory()
    payload = b"PLAINTEXT-MARKER-12345"
    created = upload(client, user["headers"], "secret.txt", payload)
    doc_id = created.json()["document_id"]

    stored = DocumentRepository.get(doc_id)
    blob = (settings.UPLOAD_DIR / stored["stored_filename"]).read_bytes()
    assert payload not in blob
    assert len(blob) == len(payload) + 28  # nonce(12) + ciphertext + tag(16)


def test_cyrillic_filename_header(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "звіт за 2026.txt", b"data")
    assert created.status_code == 201

    response = client.get(
        f"/api/v1/documents/{created.json()['document_id']}/download",
        headers=user["headers"],
    )
    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    assert "filename*=UTF-8''" in disposition
    assert "\\xd0" not in disposition


def test_newline_in_filename_is_stripped(client, user_factory, sample_pdf):
    user = user_factory()
    created = upload(
        client, user["headers"], 'a\r\nX-Evil: 1.pdf', sample_pdf, "application/pdf"
    )
    assert created.status_code == 201
    assert "\n" not in created.json()["original_filename"]

    response = client.get(
        f"/api/v1/documents/{created.json()['document_id']}/download",
        headers=user["headers"],
    )
    assert response.status_code == 200
    assert "\n" not in response.headers["content-disposition"]


def test_path_traversal_filename_is_basename(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "../../evil.txt", b"data")
    assert created.status_code == 201
    assert created.json()["original_filename"] == "evil.txt"


def test_oversized_upload_rejected(client, user_factory, monkeypatch):
    user = user_factory()
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE", 100)

    response = upload(client, user["headers"], "big.txt", b"x" * 500)
    assert response.status_code == 413


def test_forbidden_extension_rejected(client, user_factory):
    user = user_factory()
    response = upload(client, user["headers"], "payload.exe", b"MZ\x90\x00")
    assert response.status_code == 400


def test_magic_bytes_mismatch_rejected(client, user_factory):
    user = user_factory()
    response = upload(
        client, user["headers"], "fake.pdf", b"this is not a pdf", "application/pdf"
    )
    assert response.status_code == 400


def test_user_cannot_download_foreign_document(client, user_factory):
    owner = user_factory()
    stranger = user_factory()

    created = upload(client, owner["headers"], "private.txt", b"owner only")
    doc_id = created.json()["document_id"]

    response = client.get(
        f"/api/v1/documents/{doc_id}/download", headers=stranger["headers"]
    )
    assert response.status_code == 403


def test_list_returns_only_own_documents(client, user_factory):
    owner = user_factory()
    stranger = user_factory()

    upload(client, owner["headers"], "mine.txt", b"one")
    upload(client, stranger["headers"], "theirs.txt", b"two")

    mine = client.get("/api/v1/documents", headers=owner["headers"]).json()
    assert mine["count"] == 1
    assert mine["documents"][0]["original_filename"] == "mine.txt"


def test_ciphertext_swap_is_detected(client, user_factory):
    user = user_factory()
    first = upload(client, user["headers"], "first.txt", b"first content")
    second = upload(client, user["headers"], "second.txt", b"second content")

    first_id = first.json()["document_id"]
    second_id = second.json()["document_id"]

    first_meta = DocumentRepository.get(first_id)
    second_meta = DocumentRepository.get(second_id)

    first_path = settings.UPLOAD_DIR / first_meta["stored_filename"]
    second_path = settings.UPLOAD_DIR / second_meta["stored_filename"]
    shutil.copyfile(second_path, first_path)

    response = client.get(
        f"/api/v1/documents/{first_id}/download", headers=user["headers"]
    )
    assert response.status_code == 409
    assert "InvalidTag" in response.text or "фальсифіковано" in response.text


def test_tampered_file_detected(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "integrity.txt", b"integrity payload")
    doc_id = created.json()["document_id"]

    meta = DocumentRepository.get(doc_id)
    path = settings.UPLOAD_DIR / meta["stored_filename"]
    blob = bytearray(path.read_bytes())
    blob[20] ^= 0xFF
    path.write_bytes(bytes(blob))

    response = client.get(
        f"/api/v1/documents/{doc_id}/download", headers=user["headers"]
    )
    assert response.status_code == 409


def test_delete_removes_file_and_metadata(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "delete.txt", b"to delete")
    doc_id = created.json()["document_id"]

    meta = DocumentRepository.get(doc_id)
    path = settings.UPLOAD_DIR / meta["stored_filename"]
    assert path.exists()

    assert (
        client.delete(f"/api/v1/documents/{doc_id}", headers=user["headers"]).status_code
        == 200
    )
    assert not path.exists()
    assert DocumentRepository.get(doc_id) is None


def test_comments_are_sanitized(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "commented.txt", b"data")
    doc_id = created.json()["document_id"]

    response = client.post(
        f"/api/v1/documents/{doc_id}/comments",
        headers=user["headers"],
        json={"title": "XSS", "comment": "<img src=x onerror=alert(1)>text"},
    )
    assert response.status_code == 201
    stored = response.json()["sanitized_comment"]
    assert "<img" not in stored
    assert "onerror" not in stored

    listed = client.get(
        f"/api/v1/documents/{doc_id}/comments", headers=user["headers"]
    )
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
