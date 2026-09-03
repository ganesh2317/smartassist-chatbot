import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)


def _csv(value: str) -> list[str]:
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(value, minimum)


def _float_env(name: str, default: float, minimum: float = 0.1) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(value, minimum)


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    secret_key: str
    cors_origins: list[str]
    ai_api_key: str
    ai_base_url: str
    ai_model: str
    ai_timeout: float
    max_message_chars: int
    max_history_messages: int
    auth_rate_limit_per_minute: int
    chat_rate_limit_per_minute: int
    upload_rate_limit_per_minute: int
    max_upload_mb: int
    max_document_chars: int
    max_documents_per_user: int
    rag_top_k: int
    rag_max_context_chars: int


def get_settings() -> Settings:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    database_url = os.getenv("DATABASE_URL", "sqlite:///./data/smartassist.db").strip()
    secret_key = os.getenv("SECRET_KEY", "").strip()

    if not secret_key:
        raise RuntimeError("SECRET_KEY is required. Set it in backend/.env or the deployment environment.")
    if app_env == "production" and database_url.startswith("sqlite"):
        raise RuntimeError("Production requires a persistent DATABASE_URL (PostgreSQL recommended).")

    cors = _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"))

    return Settings(
        app_env=app_env,
        database_url=database_url,
        secret_key=secret_key,
        cors_origins=cors,
        ai_api_key=os.getenv("AI_API_KEY", "").strip(),
        ai_base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        ai_model=os.getenv("AI_MODEL", "gpt-4o-mini").strip(),
        ai_timeout=_float_env("AI_TIMEOUT", 30.0),
        max_message_chars=_int_env("MAX_MESSAGE_CHARS", 8000),
        max_history_messages=_int_env("MAX_HISTORY_MESSAGES", 16),
        auth_rate_limit_per_minute=_int_env("AUTH_RATE_LIMIT_PER_MINUTE", 10),
        chat_rate_limit_per_minute=_int_env("CHAT_RATE_LIMIT_PER_MINUTE", 30),
        upload_rate_limit_per_minute=_int_env("UPLOAD_RATE_LIMIT_PER_MINUTE", 8),
        max_upload_mb=_int_env("MAX_UPLOAD_MB", 10),
        max_document_chars=_int_env("MAX_DOCUMENT_CHARS", 1_500_000),
        max_documents_per_user=_int_env("MAX_DOCUMENTS_PER_USER", 50),
        rag_top_k=_int_env("RAG_TOP_K", 5),
        rag_max_context_chars=_int_env("RAG_MAX_CONTEXT_CHARS", 8000),
    )
