from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_current_user
from app.schemas import SigningKeyExport
from app.services import signing as signing_service

router = APIRouter()


@router.get("/api/v1/signing/keys")
def get_signing_keys(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "key": signing_service.find_key_info(current_user["user_id"]),
    }


@router.post("/api/v1/signing/keys")
def create_signing_keys(current_user: dict = Depends(get_current_user)):
    return {
        "status": "success",
        "key": signing_service.get_key_info(current_user["user_id"]),
    }


@router.get("/api/v1/signing/keys/public")
def download_public_key(current_user: dict = Depends(get_current_user)):
    pem = signing_service.get_public_key_pem(current_user["user_id"])
    return Response(
        content=pem,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": 'attachment; filename="docvault-public-key.pem"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/api/v1/signing/keys/export")
def export_private_key(
    payload: SigningKeyExport,
    current_user: dict = Depends(get_current_user),
):
    pem = signing_service.export_private_key(
        current_user["user_id"], payload.passphrase
    )
    return Response(
        content=pem,
        media_type="application/x-pem-file",
        headers={
            "Content-Disposition": 'attachment; filename="docvault-private-key.pem"',
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
    )
