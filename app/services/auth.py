from __future__ import annotations

import config as settings
from app.logging_config import audit
from app.repositories.users import UserRepository
from app.security.passwords import PasswordHandler
from app.services.errors import (
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
    ValidationError,
)
from utils.validators.password_validator import PasswordValidator
from utils.validators.user_validator import UserValidator


def register(
    username: str,
    email: str,
    password: str,
    *,
    client_ip: str,
) -> dict:
    clean_username = username.strip()
    clean_email = str(email).strip().lower()

    _, user_errors = UserValidator.validate_username(clean_username)
    _, email_errors = UserValidator.validate_email(clean_email)
    _, pass_errors = PasswordValidator.validate_password_complexity(password)

    field_errors: dict[str, list[str]] = {}

    def add_errors(field: str, messages: list[str]) -> None:
        if messages:
            field_errors.setdefault(field, []).extend(messages)

    add_errors("username", user_errors)
    add_errors("email", email_errors)
    add_errors("password", pass_errors)

    # Перевіряємо зайнятість лише для полів, формат яких уже коректний,
    # щоб не показувати безглузді повідомлення про дублікати.
    if not user_errors and UserRepository.username_exists(clean_username):
        add_errors("username", ["Це ім'я користувача уже існує"])
    if not email_errors and UserRepository.email_exists(clean_email):
        add_errors("email", ["Ця електронна пошта уже існує"])

    all_errors = [
        message for messages in field_errors.values() for message in messages
    ]
    if all_errors:
        raise ValidationError(all_errors, field_errors=field_errors)

    try:
        hashed_password = PasswordHandler.hash_password(password)
    except ValueError as exc:
        raise ValidationError([str(exc)]) from exc

    created = UserRepository.create(clean_username, clean_email, hashed_password)
    if not created:
        raise BadRequestError("Користувач з таким ім'ям або email уже існує.")

    audit("register", user=clean_username, ip=client_ip)
    return {
        "message": "Користувач успішно зареєстрований",
        "username": clean_username,
    }


def authenticate(
    username: str,
    password: str,
    *,
    client_ip: str,
) -> dict:
    username = username.strip()
    _, login_errors = UserValidator.validate_login_input(username)

    field_errors: dict[str, list[str]] = {}
    if login_errors:
        field_errors["username"] = login_errors
    if not password:
        field_errors["password"] = ["Пароль є обов'язковим"]

    if field_errors:
        errors = [
            message for messages in field_errors.values() for message in messages
        ]
        raise ValidationError(errors, message="Помилки валідації", field_errors=field_errors)

    user = UserRepository.get_by_username(username)

    if user:
        locked, remaining = UserRepository.is_locked(user)
        if locked:
            audit("login_locked", user=username, ip=client_ip)
            raise TooManyRequestsError(
                "Обліковий запис тимчасово заблоковано через невдалі спроби входу. "
                f"Спробуйте через {remaining} секунд.",
                headers={"Retry-After": str(max(1, remaining))},
            )
    else:
        PasswordHandler.dummy_verify(password)

    if not user or not PasswordHandler.verify_password(
        password, user.get("password_hash")
    ):
        if user:
            UserRepository.record_failed_login(
                user["id"], settings.MAX_FAILED_LOGINS, settings.LOCKOUT_MINUTES
            )
        audit("login_failed", user=username, ip=client_ip)
        raise UnauthorizedError("Невірне ім'я користувача або пароль.")

    if not user.get("is_active"):
        audit("login_inactive", user=username, ip=client_ip)
        raise ForbiddenError("Обліковий запис деактивовано.")

    UserRepository.reset_failed_logins(user["id"])
    audit("login_success", user=username, ip=client_ip)
    return user


def get_profile(current_user: dict) -> dict:
    user = UserRepository.get_by_id(current_user["user_id"])
    if not user:
        raise NotFoundError("Користувача не знайдено")

    return {
        "status": "success",
        "message": "Доступ надано!",
        "user_data": {
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "created_at": user.get("created_at"),
        },
    }
