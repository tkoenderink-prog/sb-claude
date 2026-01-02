"""Multi-LLM client configuration for council providers."""

import os
from typing import TypedDict


class ProviderConfig(TypedDict):
    """Configuration for a single LLM provider."""
    models: dict[str, str]
    env_key: str


# Provider configurations
PROVIDER_CONFIGS: dict[str, ProviderConfig] = {
    "anthropic": {
        "models": {
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-5-20250929",
        },
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "models": {
            "mini": "gpt-4o-mini",
            "standard": "gpt-4o",
        },
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        "models": {
            "flash": "gemini/gemini-2.0-flash-exp",
            "pro": "gemini/gemini-1.5-pro",
        },
        "env_key": "GOOGLE_API_KEY",
    },
}


def get_available_providers() -> list[str]:
    """Get list of providers with valid API keys."""
    available = []
    for provider, config in PROVIDER_CONFIGS.items():
        if os.getenv(config["env_key"]):
            available.append(provider)
    return available


def validate_provider_setup() -> dict[str, bool]:
    """Check which providers are configured."""
    return {
        provider: bool(os.getenv(config["env_key"]))
        for provider, config in PROVIDER_CONFIGS.items()
    }
