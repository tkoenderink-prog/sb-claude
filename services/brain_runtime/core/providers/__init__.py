"""LLM provider adapters for chat functionality.

This module provides unified interfaces to different LLM providers (Anthropic, OpenAI)
with support for streaming, tool calling, and consistent event formats.
"""

import logging
from typing import Any, Dict, List
from enum import Enum

from .base import BaseProvider, ProviderModel, ModelCapability
from .anthropic import AnthropicProvider
from .openai import OpenAIProvider

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported LLM providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


# Registry of available providers
PROVIDER_CLASSES: Dict[str, type[BaseProvider]] = {
    ProviderType.ANTHROPIC: AnthropicProvider,
    ProviderType.OPENAI: OpenAIProvider,
}


def get_provider(provider_type: str, api_key: str) -> BaseProvider:
    """Get a provider instance.

    Args:
        provider_type: Type of provider ("anthropic" or "openai")
        api_key: API key for the provider

    Returns:
        Initialized provider instance

    Raises:
        ValueError: If provider type is not supported or API key is missing
    """
    if not api_key:
        raise ValueError(f"API key required for provider '{provider_type}'")

    provider_class = PROVIDER_CLASSES.get(provider_type)
    if not provider_class:
        supported = ", ".join(PROVIDER_CLASSES.keys())
        raise ValueError(
            f"Unsupported provider '{provider_type}'. Supported: {supported}"
        )

    logger.info(f"Initializing {provider_type} provider")
    return provider_class(api_key=api_key)


def list_providers() -> List[Dict[str, Any]]:
    """List all available providers with their capabilities.

    Returns:
        List of provider info dictionaries
    """
    providers = []
    for provider_type in PROVIDER_CLASSES.keys():
        providers.append(
            {
                "type": provider_type,
                "name": provider_type.title(),
            }
        )
    return providers


def get_provider_models(provider_type: str) -> List[Dict[str, Any]]:
    """Get available models for a provider without initializing it.

    Args:
        provider_type: Type of provider

    Returns:
        List of model info dictionaries

    Raises:
        ValueError: If provider type is not supported
    """
    provider_class = PROVIDER_CLASSES.get(provider_type)
    if not provider_class:
        supported = ", ".join(PROVIDER_CLASSES.keys())
        raise ValueError(
            f"Unsupported provider '{provider_type}'. Supported: {supported}"
        )

    # Access class-level MODELS attribute
    if hasattr(provider_class, "MODELS"):
        return [model.to_dict() for model in provider_class.MODELS]
    return []


__all__ = [
    "BaseProvider",
    "ProviderModel",
    "ModelCapability",
    "AnthropicProvider",
    "OpenAIProvider",
    "ProviderType",
    "get_provider",
    "list_providers",
    "get_provider_models",
]
