from __future__ import annotations

import logging
import sqlite3

from config import DB_PATH

from app.repositories.database import database

logger = logging.getLogger("db")

SCHEMA_VERSION = 1


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, ddl: str
) -> None:
    existing = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        logger.info("Міграція: додаю колонку %s.%s", table, column)
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_schema() -> None:
    with database() as connection:
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_active INTEGER NOT NULL DEFAULT 1,
                failed_logins INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                owner_id INTEGER NOT NULL,
                content_type TEXT,
                original_size INTEGER NOT NULL DEFAULT 0,
                file_size INTEGER NOT NULL,
                sha256 TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                author_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                comment TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE,
                FOREIGN KEY (author_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_tokens (
                jti TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                family_id TEXT,
                reason TEXT,
                revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS revoked_families (
                family_id TEXT PRIMARY KEY,
                reason TEXT,
                revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        _ensure_column(connection, "users", "is_active", "INTEGER NOT NULL DEFAULT 1")
        _ensure_column(
            connection, "users", "failed_logins", "INTEGER NOT NULL DEFAULT 0"
        )
        _ensure_column(connection, "users", "locked_until", "TEXT")
        _ensure_column(connection, "users", "updated_at", "TIMESTAMP")
        _ensure_column(connection, "documents", "content_type", "TEXT")
        _ensure_column(
            connection, "documents", "original_size", "INTEGER NOT NULL DEFAULT 0"
        )
        _ensure_column(connection, "documents", "sha256", "TEXT")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_owner ON documents(owner_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_comments_document "
            "ON document_comments(document_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_revoked_expires ON revoked_tokens(expires_at)"
        )

        cursor.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    logger.info("БД ініціалізовано: %s", DB_PATH)
