from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status

from app.dependencies import get_current_user
from app.schemas import DocumentComment
from app.services import documents as document_service

router = APIRouter()


@router.get("/api/v1/documents")
def list_documents(current_user: dict = Depends(get_current_user)):
    documents = document_service.list_documents(current_user)
    return {
        "status": "success",
        "count": len(documents),
        "documents": documents,
    }


@router.post("/api/v1/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    return await document_service.upload(
        file,
        request.headers.get("content-length"),
        current_user,
    )


@router.get("/api/v1/documents/{doc_id}")
def get_document_metadata(
    doc_id: str, current_user: dict = Depends(get_current_user)
):
    document = document_service.get_document(doc_id, current_user)
    return {"status": "success", "document": document}


@router.get("/api/v1/documents/{doc_id}/download")
def download_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    result = document_service.download(doc_id, current_user)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers=result.headers,
    )


@router.delete("/api/v1/documents/{doc_id}")
def delete_document(doc_id: str, current_user: dict = Depends(get_current_user)):
    document_service.delete(doc_id, current_user)
    return {"status": "success", "message": "Документ видалено"}


@router.post(
    "/api/v1/documents/{doc_id}/comments",
    status_code=status.HTTP_201_CREATED,
)
def add_document_comment(
    doc_id: str,
    doc: DocumentComment,
    current_user: dict = Depends(get_current_user),
):
    result = document_service.add_comment(
        doc_id, doc.title, doc.comment, current_user
    )
    return {
        "status": "success",
        "comment": result["comment"],
        "original_comment": result["original_comment"],
        "sanitized_comment": result["sanitized_comment"],
    }


@router.get("/api/v1/documents/{doc_id}/comments")
def list_document_comments(
    doc_id: str, current_user: dict = Depends(get_current_user)
):
    comments = document_service.list_comments(doc_id, current_user)
    return {"status": "success", "count": len(comments), "comments": comments}
