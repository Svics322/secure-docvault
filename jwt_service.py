import jwt
import datetime
import os

SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "e4d91a82f3c7410b952d8e6a1f3c5b7e9a0c2d4f6a8b1e3c5d7f9a2b4c6d8e0f"
)
ALGORITHM = "HS256"

REVOKED_REFRESH_TOKENS = set()

def create_access_token(user_id: int, username: str, role: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": now + datetime.timedelta(minutes=15),
        "iat": now,
        "type": "access"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "exp": now + datetime.timedelta(days=7),
        "iat": now,
        "type": "refresh"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Термін дії токена минув (Expired Token)")
    except jwt.InvalidTokenError:
        raise ValueError("Недійсний підпис або пошкоджений токен (Invalid Token)")

def revoke_refresh_token(token: str) -> None:
    REVOKED_REFRESH_TOKENS.add(token)

def is_token_revoked(token: str) -> bool:
    return token in REVOKED_REFRESH_TOKENS