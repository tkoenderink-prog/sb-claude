"""Encryption utilities for API key storage in Phase 9."""

import os
from pathlib import Path
from cryptography.fernet import Fernet


def get_encryption_key() -> bytes:
    """Get or generate encryption key for API key storage.

    Priority:
    1. Environment variable API_KEY_ENCRYPTION_KEY
    2. Local file data/secrets/encryption.key (auto-generated if missing)
    """
    env_key = os.getenv("API_KEY_ENCRYPTION_KEY")
    if env_key:
        return env_key.encode()

    # Fallback to local file (for development)
    key_path = Path("data/secrets/encryption.key")
    if key_path.exists():
        return key_path.read_bytes()

    # Generate new key (first run)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    print(f"Generated new encryption key at {key_path}")
    print("Back up this file! Loss means losing access to stored API keys.")
    return key


# Initialize Fernet cipher once at module load
_fernet = None


def _get_fernet() -> Fernet:
    """Get the Fernet cipher, initializing lazily."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(get_encryption_key())
    return _fernet


def encrypt_api_key(key: str) -> str:
    """Encrypt an API key for database storage."""
    return _get_fernet().encrypt(key.encode()).decode()


def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key from database storage."""
    return _get_fernet().decrypt(encrypted.encode()).decode()


def get_key_suffix(key: str) -> str:
    """Get last 4 characters for display (e.g., '...7x2Q')."""
    return key[-4:] if len(key) >= 4 else key
