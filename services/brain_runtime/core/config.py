"""Configuration management for the Brain Runtime service."""

from typing import Optional, Literal
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service configuration
    service_name: str = "brain-runtime"
    version: str = "0.1.0"
    debug: bool = False

    # Development mode: 'local' or 'docker'
    # Set by dev scripts to indicate which environment is running
    dev_mode: Literal["local", "docker", "production"] = "local"
    dev_port: int = 8000  # Port this instance is running on

    # API Keys
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Vault configuration
    obsidian_location: Optional[str] = None  # Parent dir (local dev)
    obsidian_vault_path: Optional[str] = None  # Direct vault path (Docker)

    def get_vault_path(self) -> Optional[str]:
        """Get the vault path - prefers obsidian_vault_path, falls back to obsidian_location/Obsidian-Private."""
        if self.obsidian_vault_path:
            return self.obsidian_vault_path
        if self.obsidian_location:
            from pathlib import Path
            return str(Path(self.obsidian_location) / "Obsidian-Private")
        return None

    # Calendar configuration
    calendar_work_url: Optional[str] = None
    calendar_private_url: Optional[str] = None

    # Database configuration
    database_url: str = "postgresql://secondbrain:changeme_in_production@localhost:5432/second_brain"

    # Data directory (for locks, exports, etc.)
    # In Docker: /app/data, locally: project_root/data
    data_path: Optional[str] = None

    # ChromaDB configuration
    chroma_host: str = "localhost"
    chroma_port: int = 8002

    # CORS settings - includes both dev ports and Tailscale IP
    # Set CORS_ORIGINS env var to add additional origins (comma-separated)
    cors_origins: list[str] = [
        "http://localhost:3000",  # Docker frontend
        "http://localhost:3001",  # Local frontend
        "http://100.91.159.89:3000",  # Tailscale IP
        "http://100.91.159.89:3001",
    ]

    class Config:
        env_file = "../../.env"  # Path from services/brain_runtime/ to project root
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env file


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
