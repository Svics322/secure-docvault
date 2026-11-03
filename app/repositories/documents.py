from __future__ import annotations

import logging
import sqlite3

from app.repositories.database import database

logger = logging.getLogger("db.documents")


class DocumentRepository:
    @staticmethod
    def save(
        doc_id: str,
        original_filename: str,
        stored_filename: str,
        owner_id: int,
        file_size: int,
        *,
        content_type: str | None = None,
        original_size: int = 0,
        sha256: str | None = None,
    ) -> bool:
        try:
            with database() as connection:
                connection.execute(
                    """
                    INSERT INTO documents (
                        id, original_filename, stored_filename, owner_id,
                        content_type, original_size, file_size, sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        doc_id,
                        original_filename,
                        stored_filename,
                        owner_id,
                        content_type,
                        original_size,
                        file_size,
                        sha256,
                    ),
                )
            return True
        except sqlite3.Error:
            logger.exception("Не вдалося зберегти метадані документа %s", doc_id)
            return False

    @staticmethod
    def get(doc_id: str) -> dict | None:
        with database() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_for_owner(owner_id: int, is_admin: bool = False) -> list[dict]:
        with database() as connection:
            if is_admin:
                rows = connection.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM documents WHERE owner_id = ? "
                    "ORDER BY created_at DESC",
                    (owner_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def delete(doc_id: str) -> bool:
        with database() as connection:
            cursor = connection.execute(
                "DELETE FROM documents WHERE id = ?", (doc_id,)
            )
            return cursor.rowcount > 0
