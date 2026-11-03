import os
from pathlib import Path

from dotenv import load_dotenv

# Корінь проєкту не залежить від робочої директорії процесу.
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return Path(raw).expanduser().resolve()


# ---------------------------------------------------------------------------
# Клієнт (використовується PySide6-застосунком)
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# ---------------------------------------------------------------------------
# Сервер
# ---------------------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "127.0.0.1")
API_PORT = _env_int("API_PORT", 8000)
DEBUG = _env_bool("DEBUG", False)

DATA_DIR = _env_path("DOCVAULT_DATA_DIR", PROJECT_ROOT)
DB_PATH = _env_path("DOCVAULT_DB_PATH", DATA_DIR / "docvault.db")
UPLOAD_DIR = _env_path("DOCVAULT_UPLOAD_DIR", DATA_DIR / "uploads")
LOG_DIR = _env_path("DOCVAULT_LOG_DIR", DATA_DIR / "logs")
WEB_DIR = PROJECT_ROOT / "web"

# ---------------------------------------------------------------------------
# Завантаження файлів
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE = _env_int("MAX_UPLOAD_SIZE", 10 * 1024 * 1024)  # 10 MiB
UPLOAD_CHUNK_SIZE = 1024 * 1024

_DEFAULT_EXTENSIONS = "pdf,png,jpg,jpeg,gif,txt,csv,md,docx,xlsx,pptx,zip"
ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.getenv("ALLOWED_EXTENSIONS", _DEFAULT_EXTENSIONS).split(",")
    if ext.strip()
}

# ---------------------------------------------------------------------------
# Cookie / CSRF
# ---------------------------------------------------------------------------
COOKIE_SECURE = _env_bool("COOKIE_SECURE", True)
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "strict").lower()
ACCESS_COOKIE_NAME = "access_token"
REFRESH_COOKIE_NAME = "refresh_token"
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
ACCESS_TOKEN_TTL_MINUTES = 15
REFRESH_TOKEN_TTL_DAYS = 7
JWT_ISSUER = "secure-docvault"
JWT_AUDIENCE = "secure-docvault-api"

# Ключі, які вже потрапили в публічні коміти / приклади. Старт із ними заборонений.
LEAKED_JWT_SECRETS = {
    "e4d91a82f3c7410b952d8e6a1f3c5b7e9a0c2d4f6a8b1e3c5d7f9a2b4c6d8e0f",
    "b39f1c7d2e8a45f90a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f",
    "secret",
    "changeme",
    "dev-secret",
}

# ---------------------------------------------------------------------------
# Обмеження входу
# ---------------------------------------------------------------------------
RATE_LIMIT_LOGIN = 5
RATE_LIMIT_LOGIN_WINDOW = 60
RATE_LIMIT_GENERAL = 60
RATE_LIMIT_GENERAL_WINDOW = 60
RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", True)

WAF_ENABLED = _env_bool("WAF_ENABLED", True)
WAF_BAN_SECONDS = 300
WAF_BAN_MAX_ENTRIES = 10_000
WAF_MAX_BODY_INSPECTION = 64 * 1024

# Блокування облікового запису після серії невдалих спроб
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

# Довіряти заголовку X-Forwarded-For (лише за reverse-proxy)
TRUST_PROXY = _env_bool("TRUST_PROXY", False)
