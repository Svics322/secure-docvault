from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import config as settings

router = APIRouter()


def web_client_available() -> bool:
    return settings.WEB_DIR.exists()


@router.get("/", include_in_schema=False)
def web_app() -> FileResponse:
    return FileResponse(settings.WEB_DIR / "index.html")


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    icon = settings.PROJECT_ROOT / "icons.ico"
    if not icon.is_file():
        raise HTTPException(status_code=404, detail="Іконку не знайдено")

    return FileResponse(
        icon,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=86400"},
    )
