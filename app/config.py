"""
Application configuration using Pydantic Settings.
Allows configuration via environment variables or .env file with sensible defaults
for local development, Wi-Fi LAN testing, and free-tier cloud hosting (e.g. Render).
"""
import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bulk Certificate Generator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Base project directory
    BASE_DIR: Path = BASE_DIR

    # Base URL for QR code verification links.
    # Configurable via environment variable or .env file:
    # - Local / Same machine: http://localhost:8000
    # - Local Wi-Fi / Phone testing: http://192.168.1.9:8000
    # - Production (Render): https://your-app.onrender.com
    BASE_URL: str = "http://localhost:8000"

    # SQLite Database URL
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/certificates.db"

    # Directory to store generated PDF certificates
    STORAGE_DIR: Path = BASE_DIR / "certificates"

    @field_validator("BASE_URL")
    @classmethod
    def clean_base_url(cls, v: str) -> str:
        """Strip whitespace and trailing slashes for clean URL concatenation."""
        return v.strip().rstrip("/")

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

# Ensure the certificates directory exists on startup
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
