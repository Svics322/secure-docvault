from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import DEBUG, LOG_DIR

_CONFIGURED = False
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if DEBUG else logging.INFO

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    app_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    root.addHandler(app_handler)

    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    audit_logger.handlers.clear()
    audit_handler = RotatingFileHandler(
        LOG_DIR / "audit.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    audit_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    audit_logger.addHandler(audit_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


def _escape(value: object) -> str:
    return str(value).replace("\n", " ").replace("\r", " ").replace("|", "/")


def audit(event: str, **fields: object) -> None:
    details = " ".join(f"{key}={_escape(value)}" for key, value in fields.items())
    logging.getLogger("audit").info("event=%s %s", event, details)
