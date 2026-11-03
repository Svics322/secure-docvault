from __future__ import annotations

import bcrypt

MAX_PASSWORD_BYTES = 72
BCRYPT_ROUNDS = 12


class PasswordHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        encoded = password.encode("utf-8")
        if len(encoded) > MAX_PASSWORD_BYTES:
            raise ValueError("Пароль перевищує 72 байти")
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        return bcrypt.hashpw(encoded, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str | None) -> bool:
        if not hashed_password:
            return False
        try:
            encoded = plain_password.encode("utf-8")
            if len(encoded) > MAX_PASSWORD_BYTES:
                return False
            return bcrypt.checkpw(encoded, hashed_password.encode("utf-8"))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def dummy_verify(plain_password: str) -> None:
        PasswordHandler.verify_password(plain_password, _DUMMY_HASH)


_DUMMY_HASH = bcrypt.hashpw(
    b"docvault-dummy-password-for-timing", bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
).decode("utf-8")
