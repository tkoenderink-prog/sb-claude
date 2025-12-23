"""Configuration management for the Brain Runtime service."""

from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    service_name: str = "brain-runtime"
    version: str = "0.1.0"
    debug: bool = False

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Vault configuration
    obsidian_location: Optional[str] = None

    # Calendar configuration
    calendar_work_url: Optional[str] = None
    calendar_private_url: Optional[str] = None

    # Database configuration (for future use)
    database_url: str = "postgresql://tijlkoenderink@localhost:5432/second_brain"

    # CORS settings - includes Tailscale IP range for remote access
    # Set CORS_ORIGINS env var to add additional origins (comma-separated)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://100.91.159.89:3000",  # Tailscale IP
    ]

    class Config:
        env_file = "../../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
