from __future__ import annotations

from datetime import datetime

from app.repositories.database import database, to_db_time, utcnow


class TokenRepository:
    @staticmethod
    def revoke(
        jti: str,
        user_id: int,
        expires_at: datetime,
        family_id: str | None = None,
        reason: str = "rotation",
    ) -> None:
        with database() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO revoked_tokens
                    (jti, user_id, family_id, reason, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (jti, user_id, family_id, reason, to_db_time(expires_at)),
            )

    @staticmethod
    def revoke_family(family_id: str, reason: str = "replay_detected") -> int:
        with database() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO revoked_families (family_id, reason) "
                "VALUES (?, ?)",
                (family_id, reason),
            )
            cursor = connection.execute(
                "UPDATE revoked_tokens SET reason = ? WHERE family_id = ?",
                (reason, family_id),
            )
            return cursor.rowcount

    @staticmethod
    def is_family_revoked(family_id: str) -> bool:
        with database() as connection:
            row = connection.execute(
                "SELECT 1 FROM revoked_families WHERE family_id = ?", (family_id,)
            ).fetchone()
            return row is not None

    @staticmethod
    def is_revoked(jti: str) -> bool:
        with database() as connection:
            row = connection.execute(
                "SELECT 1 FROM revoked_tokens WHERE jti = ?", (jti,)
            ).fetchone()
            return row is not None

    @staticmethod
    def purge_expired() -> int:
        with database() as connection:
            cursor = connection.execute(
                "DELETE FROM revoked_tokens WHERE expires_at < ?",
                (to_db_time(utcnow()),),
            )
            connection.execute(
                "DELETE FROM revoked_families "
                "WHERE revoked_at < datetime('now', '-8 days')"
            )
            return cursor.rowcount
