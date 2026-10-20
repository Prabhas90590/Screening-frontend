import os
from dataclasses import dataclass


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
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./screening.db")
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
    debug: bool = _get_bool("DEBUG", True)


settings = Settings()
