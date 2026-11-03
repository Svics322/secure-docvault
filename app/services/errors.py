from __future__ import annotations

from typing import Any


class AppError(Exception):
    status_code = 400
    default_detail: Any = "Помилка запиту"

    def __init__(
        self,
        detail: Any = None,
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.detail = self.default_detail if detail is None else detail
        self.headers = headers or {}
        super().__init__(
            self.detail if isinstance(self.detail, str) else str(self.detail)
        )


class ValidationError(AppError):
    status_code = 400
    default_detail = "Помилки валідації даних"

    def __init__(
        self,
        errors: list[str],
        *,
        message: str = "Помилки валідації даних",
        field_errors: dict[str, list[str]] | None = None,
    ) -> None:
        detail: dict[str, Any] = {"message": message, "errors": errors}
        if field_errors:
            detail["field_errors"] = field_errors
        super().__init__(detail)


class BadRequestError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class PayloadTooLargeError(AppError):
    status_code = 413


class TooManyRequestsError(AppError):
    status_code = 429


class InternalError(AppError):
    status_code = 500
    default_detail = "Внутрішня помилка сервера"
