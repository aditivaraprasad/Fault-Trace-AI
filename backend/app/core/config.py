from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "FAULTTRACE AI"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database configuration (PostgreSQL with SQLite fallback)
    DATABASE_URL: str = "sqlite:///./faulttrace.db"

    # Weather API integration flag
    OPEN_METEO_ENABLED: bool = False

    # Pipeline configuration
    CORRELATION_WINDOW_MINUTES: int = 15
    CALIBRATION_METHOD: str = "isotonic"

    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
