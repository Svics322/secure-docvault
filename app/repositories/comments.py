from __future__ import annotations

from app.repositories.database import database


class CommentRepository:
    @staticmethod
    def add(document_id: str, author_id: int, title: str, comment: str) -> dict:
        with database() as connection:
            cursor = connection.execute(
                "INSERT INTO document_comments (document_id, author_id, title, comment) "
                "VALUES (?, ?, ?, ?)",
                (document_id, author_id, title, comment),
            )
            return {
                "id": cursor.lastrowid,
                "document_id": document_id,
                "author_id": author_id,
                "title": title,
                "comment": comment,
            }

    @staticmethod
    def list_for_document(document_id: str) -> list[dict]:
        with database() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.document_id, c.title, c.comment, c.created_at,
                       u.username AS author
                  FROM document_comments c
                  JOIN users u ON u.id = c.author_id
                 WHERE c.document_id = ?
                 ORDER BY c.id DESC
                """,
                (document_id,),
            ).fetchall()
            return [dict(row) for row in rows]
