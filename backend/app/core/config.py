from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv_file() -> None:
    """Load key-value pairs from backend/.env into os.environ if not already set."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        # Allow .env to override or set environment variables
                        os.environ[key] = val
        except Exception:
            pass


_load_dotenv_file()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    data_provider: str = os.getenv("DATA_PROVIDER", "mock")
    vendor_api_key: str = os.getenv("VENDOR_API_KEY", "")
    vendor_base_url: str = os.getenv("VENDOR_BASE_URL", "")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screening_db"
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
    debug: bool = _get_bool("DEBUG", True)

    # Auth settings (Phase 2 – user-side login)
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "INSECURE_FALLBACK_DO_NOT_USE_IN_PRODUCTION")
    session_idle_limit: int = int(os.getenv("SESSION_IDLE_LIMIT", "1800"))
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Email & SMTP notification settings
    email_notifications_enabled: bool = _get_bool("EMAIL_NOTIFICATIONS_ENABLED", True)
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.office365.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_use_tls: bool = _get_bool("SMTP_USE_TLS", True)
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    email_from: str = os.getenv("EMAIL_FROM", "Equity Screening Platform <notifications@company.com>")
    email_to: str = os.getenv("EMAIL_TO", "")


settings = Settings()
