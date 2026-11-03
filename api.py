from __future__ import annotations

import config as settings
from app.dependencies import get_current_user
from app.main import app

__all__ = ["app", "settings", "get_current_user"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
