"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Optional, Dict, Any
from enum import Enum


class ModelCapability(str, Enum):
    """Capabilities that a model may support."""

    TOOLS = "tools"
    VISION = "vision"
    STREAMING = "streaming"
    EXTENDED_THINKING = "extended_thinking"
    PROMPT_CACHING = "prompt_caching"


class ProviderModel:
    """Model information for a provider."""

    def __init__(
        self,
        id: str,
        name: str,
        capabilities: List[ModelCapability],
        context_window: int,
        max_output: int,
        deprecated: bool = False,
    ):
        self.id = id
        self.name = name
        self.capabilities = capabilities
        self.context_window = context_window
        self.max_output = max_output
        self.deprecated = deprecated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "capabilities": [cap.value for cap in self.capabilities],
            "context_window": self.context_window,
            "max_output": self.max_output,
            "deprecated": self.deprecated,
        }


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str):
        """Initialize provider with API key.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send chat request and stream response.

        Args:
            messages: List of messages in provider format
            tools: Optional list of tools available to the model
            stream: Whether to stream the response
            model: Model ID to use (uses default if not specified)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Yields:
            Event dictionaries with structure:
            {
                "type": "content" | "tool_call" | "tool_result" | "error" | "done",
                "data": <event-specific data>
            }
        """
        pass

    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports function calling.

        Returns:
            True if provider supports tool use
        """
        pass

    @abstractmethod
    def get_models(self) -> List[ProviderModel]:
        """Get available models for this provider.

        Returns:
            List of ProviderModel objects
        """
        pass

    @abstractmethod
    def format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for this provider's API.

        Args:
            tools: List of tool definitions in standard format

        Returns:
            List of tools formatted for provider's API
        """
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model ID for this provider.

        Returns:
            Model ID string
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the provider name.

        Returns:
            Provider name (e.g., "anthropic", "openai")
        """
        pass
