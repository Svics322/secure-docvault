from __future__ import annotations

import logging
import sqlite3
from datetime import timedelta

from app.repositories.database import database, from_db_time, to_db_time, utcnow

logger = logging.getLogger("db.users")


class UserRepository:
    @staticmethod
    def create(username: str, email: str, password_hash: str) -> bool:
        try:
            with database() as connection:
                connection.execute(
                    "INSERT INTO users (username, email, password_hash, updated_at) "
                    "VALUES (?, ?, ?, ?)",
                    (username, email, password_hash, to_db_time(utcnow())),
                )
            return True
        except sqlite3.IntegrityError:
            logger.info("Реєстрація відхилена: username/email уже зайняті")
            return False

    @staticmethod
    def username_exists(username: str) -> bool:
        with database() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE username = ? LIMIT 1", (username,)
            ).fetchone()
            return row is not None

    @staticmethod
    def email_exists(email: str) -> bool:
        with database() as connection:
            row = connection.execute(
                "SELECT 1 FROM users WHERE email = ? LIMIT 1", (email,)
            ).fetchone()
            return row is not None

    @staticmethod
    def get_by_username(username: str) -> dict | None:
        with database() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_by_id(user_id: int) -> dict | None:
        with database() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def set_active(user_id: int, is_active: bool) -> None:
        with database() as connection:
            connection.execute(
                "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
                (1 if is_active else 0, to_db_time(utcnow()), user_id),
            )

    @staticmethod
    def record_failed_login(user_id: int, max_attempts: int, lock_minutes: int) -> None:
        locked_until = to_db_time(utcnow() + timedelta(minutes=lock_minutes))
        with database() as connection:
            connection.execute(
                """
                UPDATE users
                   SET failed_logins = failed_logins + 1,
                       locked_until = CASE
                           WHEN failed_logins + 1 >= ? THEN ?
                           ELSE locked_until
                       END,
                       updated_at = ?
                 WHERE id = ?
                """,
                (max_attempts, locked_until, to_db_time(utcnow()), user_id),
            )

    @staticmethod
    def reset_failed_logins(user_id: int) -> None:
        with database() as connection:
            connection.execute(
                "UPDATE users SET failed_logins = 0, locked_until = NULL, "
                "updated_at = ? WHERE id = ?",
                (to_db_time(utcnow()), user_id),
            )

    @staticmethod
    def is_locked(user: dict) -> tuple[bool, int]:
        locked_until = from_db_time(user.get("locked_until"))
        if not locked_until:
            return False, 0
        remaining = int((locked_until - utcnow()).total_seconds())
        if remaining <= 0:
            return False, 0
        return True, remaining
