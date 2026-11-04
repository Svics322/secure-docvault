from __future__ import annotations

import logging
import sqlite3

from app.repositories.database import database

logger = logging.getLogger("db.signing")


class SigningKeyRepository:
    @staticmethod
    def get(user_id: int) -> dict | None:
        with database() as connection:
            row = connection.execute(
                "SELECT * FROM user_signing_keys WHERE user_id = ?", (user_id,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def save(
        user_id: int,
        public_key_pem: str,
        private_key_encrypted: str,
        key_fingerprint: str,
        algorithm: str,
    ) -> bool:
        try:
            with database() as connection:
                connection.execute(
                    """
                    INSERT INTO user_signing_keys (
                        user_id, public_key_pem, private_key_encrypted,
                        key_fingerprint, algorithm
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        public_key_pem = excluded.public_key_pem,
                        private_key_encrypted = excluded.private_key_encrypted,
                        key_fingerprint = excluded.key_fingerprint,
                        algorithm = excluded.algorithm
                    """,
                    (
                        user_id,
                        public_key_pem,
                        private_key_encrypted,
                        key_fingerprint,
                        algorithm,
                    ),
                )
            return True
        except sqlite3.Error:
            logger.exception("Не вдалося зберегти ключі підпису user_id=%s", user_id)
            return False


class SignatureRepository:
    @staticmethod
    def get(document_id: str) -> dict | None:
        with database() as connection:
            row = connection.execute(
                "SELECT * FROM document_signatures WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def save(
        document_id: str,
        signer_id: int,
        algorithm: str,
        signature_b64: str,
        public_key_fingerprint: str,
    ) -> bool:
        try:
            with database() as connection:
                connection.execute(
                    """
                    INSERT INTO document_signatures (
                        document_id, signer_id, algorithm,
                        signature_b64, public_key_fingerprint
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(document_id) DO UPDATE SET
                        signer_id = excluded.signer_id,
                        algorithm = excluded.algorithm,
                        signature_b64 = excluded.signature_b64,
                        public_key_fingerprint = excluded.public_key_fingerprint
                    """,
                    (
                        document_id,
                        signer_id,
                        algorithm,
                        signature_b64,
                        public_key_fingerprint,
                    ),
                )
            return True
        except sqlite3.Error:
            logger.exception(
                "Не вдалося зберегти підпис документа %s", document_id
            )
            return False
