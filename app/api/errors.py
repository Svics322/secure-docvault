from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.services.errors import AppError

logger = logging.getLogger("api.errors")

FIELD_LABELS = {
    "username": "Ім'я користувача",
    "email": "Email",
    "password": "Пароль",
    "title": "Заголовок",
    "comment": "Коментар",
    "file": "Файл",
    "refresh_token": "Refresh-токен",
}


def _field_label(location: tuple[Any, ...]) -> str:
    parts = [
        part
        for part in location
        if part not in {"body", "query", "path", "header", "cookie"}
    ]
    if not parts:
        return "Дані запиту"
    name = str(parts[-1])
    return FIELD_LABELS.get(name, name.replace("_", " ").capitalize())


def _characters_word(amount: Any) -> str:
    try:
        number = abs(int(amount))
    except (TypeError, ValueError):
        return "символів"

    if number % 10 == 1 and number % 100 != 11:
        return "символ"
    if 2 <= number % 10 <= 4 and not 12 <= number % 100 <= 14:
        return "символи"
    return "символів"


def _localized_message(error: dict[str, Any]) -> str:
    error_type = str(error.get("type", ""))
    context = error.get("ctx") or {}
    field = _field_label(tuple(error.get("loc") or ()))

    if error_type == "missing":
        if field == "Файл":
            return "Оберіть файл для завантаження"
        return f"Поле «{field}» є обов'язковим"
    if error_type == "string_too_short":
        limit = context.get("min_length")
        return (
            f"Поле «{field}» має містити щонайменше "
            f"{limit} {_characters_word(limit)}"
        )
    if error_type == "string_too_long":
        limit = context.get("max_length")
        return (
            f"Поле «{field}» не повинно перевищувати "
            f"{limit} {_characters_word(limit)}"
        )
    if error_type == "string_type":
        return f"Поле «{field}» має бути текстом"
    if error_type in {"int_type", "int_parsing"}:
        return f"Поле «{field}» має бути цілим числом"
    if error_type in {"value_error", "email"} or "email" in error_type:
        if field == "Email":
            return "Некоректний формат email"
        return f"Поле «{field}» містить некоректне значення"
    if error_type == "json_invalid":
        return "Некоректний формат JSON у тілі запиту"
    if error_type == "list_type":
        return f"Поле «{field}» має бути списком"
    return f"Поле «{field}» містить некоректне значення"


def _localize_validation_errors(
    raw_errors: list[dict[str, Any]],
) -> tuple[list[str], dict[str, list[str]]]:
    errors: list[str] = []
    field_errors: dict[str, list[str]] = {}

    for raw in raw_errors:
        message = _localized_message(raw)
        if message in errors:
            continue
        errors.append(message)

        location = tuple(raw.get("loc") or ())
        field = str(location[-1]) if location else ""
        if field and field not in {"body", "query", "path", "header", "cookie"}:
            field_errors.setdefault(field, []).append(message)

    return errors, field_errors


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers or None,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors, field_errors = _localize_validation_errors(exc.errors())
        return JSONResponse(
            status_code=400,
            content={
                "detail": {
                    "message": "Помилки валідації даних",
                    "errors": errors,
                    "field_errors": field_errors,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Необроблена помилка на %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": "Internal Server Error",
                "message": "Внутрішня помилка сервера. Спробуйте пізніше.",
            },
        )
