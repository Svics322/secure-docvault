from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config as settings
from app.api.errors import register_exception_handlers
from app.api.routers import auth, documents, signing, web
from app.lifespan import lifespan
from app.logging_config import setup_logging
from app.middleware import SecurityMiddleware

setup_logging()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Secure DocVault API",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(SecurityMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", settings.CSRF_HEADER_NAME],
    )

    register_exception_handlers(application)

    application.include_router(auth.router)
    application.include_router(documents.router)
    application.include_router(signing.router)

    if web.web_client_available():
        application.mount(
            "/static", StaticFiles(directory=settings.WEB_DIR), name="static"
        )
        application.include_router(web.router)

    return application


app = create_app()

__all__ = ["app", "create_app"]
