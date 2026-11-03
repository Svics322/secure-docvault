from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

import config as settings
from app.repositories.schema import init_schema
from app.repositories.tokens import TokenRepository

logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_schema()

    purged = TokenRepository.purge_expired()
    if purged:
        logger.info("Очищено прострочених записів blacklist: %s", purged)
    logger.info(
        "Secure DocVault API запущено (upload dir=%s, max upload=%s байт)",
        settings.UPLOAD_DIR,
        settings.MAX_UPLOAD_SIZE,
    )
    yield
