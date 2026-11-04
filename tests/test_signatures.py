from __future__ import annotations

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization

from app.repositories.signing import SignatureRepository
from app.security.signatures import (
    generate_keypair,
    sign_content,
    verify_content,
)


def upload(client, headers, filename="signed.txt", content=b"signed content"):
    return client.post(
        "/api/v1/documents/upload",
        headers=headers,
        files={"file": (filename, content, "text/plain")},
    )


def test_key_generation_returns_public_pem(client, user_factory):
    user = user_factory()

    first = client.post("/api/v1/signing/keys", headers=user["headers"])
    assert first.status_code == 200, first.text
    key = first.json()["key"]

    assert key["algorithm"] == "RSA-PSS-SHA256"
    assert key["public_key_pem"].startswith("-----BEGIN PUBLIC KEY-----")
    assert len(key["fingerprint"]) == 64

    second = client.get("/api/v1/signing/keys", headers=user["headers"])
    assert second.status_code == 200
    assert second.json()["key"]["fingerprint"] == key["fingerprint"]

    public_pem = client.get(
        "/api/v1/signing/keys/public", headers=user["headers"]
    )
    assert public_pem.status_code == 200
    assert public_pem.text.startswith("-----BEGIN PUBLIC KEY-----")


def test_private_key_export_is_password_protected(client, user_factory):
    user = user_factory()

    response = client.post(
        "/api/v1/signing/keys/export",
        headers=user["headers"],
        json={"passphrase": "Aa1!aaaa"},
    )
    assert response.status_code == 200, response.text
    assert "BEGIN ENCRYPTED PRIVATE KEY" in response.text
    assert "BEGIN PRIVATE KEY" not in response.text

    private_key = serialization.load_pem_private_key(
        response.content, password=b"Aa1!aaaa"
    )
    assert private_key.key_size == 2048

    with pytest.raises(ValueError):
        serialization.load_pem_private_key(response.content, password=b"wrong")


def test_private_key_export_requires_passphrase(client, user_factory):
    user = user_factory()

    empty = client.post(
        "/api/v1/signing/keys/export",
        headers=user["headers"],
        json={"passphrase": ""},
    )
    assert empty.status_code == 400
    assert "Парольна фраза" in empty.text
    assert empty.json()["detail"]["field_errors"]["passphrase"]

    short = client.post(
        "/api/v1/signing/keys/export",
        headers=user["headers"],
        json={"passphrase": "short"},
    )
    assert short.status_code == 400


def test_upload_signs_document_and_download_reports_verified(
    client, user_factory
):
    user = user_factory()
    content = b"OFFICIAL STATEMENT: APPROVED BY CHIEF SECURITY OFFICER"

    created = upload(client, user["headers"], "official.txt", content)
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["signature"]["status"] == "signed"
    assert payload["signature"]["algorithm"] == "RSA-PSS-SHA256"

    doc_id = payload["document_id"]
    listed = client.get("/api/v1/documents", headers=user["headers"]).json()
    document = next(item for item in listed["documents"] if item["document_id"] == doc_id)
    assert document["signature"]["status"] == "signed"
    assert document["signature"]["signer"] == user["username"]

    downloaded = client.get(
        f"/api/v1/documents/{doc_id}/download", headers=user["headers"]
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["X-Signature-Status"] == "Signed & Verified"
    assert downloaded.headers["X-Signature-Algorithm"] == "RSA-PSS-SHA256"
    assert downloaded.headers["X-Signer"] == user["username"]
    assert len(downloaded.headers["X-Signature-Fingerprint"]) == 64


def test_tampered_signature_rejected_on_download(client, user_factory):
    user = user_factory()
    created = upload(client, user["headers"], "signature.txt", b"signed bytes")
    doc_id = created.json()["document_id"]

    stored = SignatureRepository.get(doc_id)
    assert stored is not None
    SignatureRepository.save(
        document_id=doc_id,
        signer_id=stored["signer_id"],
        algorithm=stored["algorithm"],
        signature_b64=base64.b64encode(os.urandom(256)).decode("ascii"),
        public_key_fingerprint=stored["public_key_fingerprint"],
    )

    response = client.get(
        f"/api/v1/documents/{doc_id}/download", headers=user["headers"]
    )
    assert response.status_code == 409
    assert "підпис" in response.text.lower()


def test_signature_module_detects_modified_content():
    private_key, public_key = generate_keypair()
    original = b"OFFICIAL STATEMENT: APPROVED"
    signature = sign_content(original, private_key)

    assert verify_content(original, signature, public_key)
    assert not verify_content(
        b"OFFICIAL STATEMENT: REJECTED", signature, public_key
    )
