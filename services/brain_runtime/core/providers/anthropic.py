"""Anthropic Claude provider implementation."""

import logging
from typing import AsyncGenerator, List, Optional, Dict, Any
from anthropic import AsyncAnthropic
from anthropic.types import Message, TextBlock, ToolUseBlock

from .base import BaseProvider, ProviderModel, ModelCapability

logger = logging.getLogger(__name__)

# Beta features to enable
BETA_HEADERS = [
    "prompt-caching-2024-07-31",  # 90% cost reduction on repeated prompts
    "extended-cache-ttl-2025-04-11",  # 1-hour cache (vs 5-min default)
    "token-efficient-tools-2025-02-19",  # Optimized tool token usage
]


class AnthropicProvider(BaseProvider):
    """Provider implementation for Anthropic Claude."""

    # Available models
    MODELS = [
        # Claude 4.5 Family (Current Generation - December 2025)
        ProviderModel(
            id="claude-opus-4-5-20251101",
            name="Claude Opus 4.5",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
                ModelCapability.EXTENDED_THINKING,
                ModelCapability.PROMPT_CACHING,
            ],
            context_window=200000,
            max_output=64000,
        ),
        ProviderModel(
            id="claude-sonnet-4-5-20250929",
            name="Claude Sonnet 4.5",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
                ModelCapability.PROMPT_CACHING,
            ],
            context_window=200000,
            max_output=64000,
        ),
        ProviderModel(
            id="claude-haiku-4-5-20251001",
            name="Claude Haiku 4.5",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.STREAMING,
                ModelCapability.PROMPT_CACHING,
            ],
            context_window=200000,
            max_output=64000,
        ),
        # Claude 4 Family (Previous Generation - Deprecated)
        ProviderModel(
            id="claude-opus-4-20250514",
            name="Claude Opus 4",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
            ],
            context_window=200000,
            max_output=16384,
            deprecated=True,
        ),
        ProviderModel(
            id="claude-sonnet-4-20250514",
            name="Claude Sonnet 4",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
            ],
            context_window=200000,
            max_output=16384,
            deprecated=True,
        ),
        # Claude 3.5 Family (Budget)
        ProviderModel(
            id="claude-3-5-haiku-20241022",
            name="Claude 3.5 Haiku",
            capabilities=[ModelCapability.TOOLS, ModelCapability.STREAMING],
            context_window=200000,
            max_output=8192,
        ),
    ]

    DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

    def __init__(self, api_key: str):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
        """
        super().__init__(api_key)
        self.client = AsyncAnthropic(
            api_key=api_key, default_headers={"anthropic-beta": ",".join(BETA_HEADERS)}
        )

    @property
    def name(self) -> str:
        """Get provider name."""
        return "anthropic"

    def get_default_model(self) -> str:
        """Get default model ID."""
        return self.DEFAULT_MODEL

    def supports_tools(self) -> bool:
        """Anthropic supports tool use."""
        return True

    def get_models(self) -> List[ProviderModel]:
        """Get available Anthropic models."""
        return self.MODELS

    @classmethod
    def get_model(cls, model_id: str) -> Optional[ProviderModel]:
        """Get a specific model by ID.

        Args:
            model_id: The model ID to look up

        Returns:
            ProviderModel if found, None otherwise
        """
        for model in cls.MODELS:
            if model.id == model_id:
                return model
        return None

    @classmethod
    def get_available_models(
        cls, include_deprecated: bool = False
    ) -> List[ProviderModel]:
        """Get available models, optionally filtering out deprecated ones.

        Args:
            include_deprecated: Whether to include deprecated models

        Returns:
            List of ProviderModel objects
        """
        if include_deprecated:
            return cls.MODELS
        return [model for model in cls.MODELS if not model.deprecated]

    def format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for Anthropic API.

        Anthropic expects:
        {
            "name": "tool_name",
            "description": "Tool description",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }

        Args:
            tools: List of tool definitions in standard format

        Returns:
            List of tools formatted for Anthropic
        """
        formatted = []
        for tool in tools:
            formatted.append(
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get(
                        "parameters",
                        {"type": "object", "properties": {}, "required": []},
                    ),
                }
            )
        return formatted

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict]] = None,
        stream: bool = True,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send chat request to Anthropic and stream response.

        Args:
            messages: List of messages (must have at least one user message)
            tools: Optional list of available tools
            stream: Whether to stream the response
            model: Model ID (defaults to claude-sonnet-4)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Event dictionaries
        """
        # Separate system message from conversation
        system_message = None
        conversation_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                conversation_messages.append(msg)

        # Default parameters
        model_id = model or self.DEFAULT_MODEL
        max_tokens = max_tokens or 4096
        temperature = temperature if temperature is not None else 1.0

        # Build request parameters
        request_params = {
            "model": model_id,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conversation_messages,
        }

        if system_message:
            request_params["system"] = system_message

        if tools:
            request_params["tools"] = self.format_tools(tools)

        try:
            if stream:
                async for event in self._stream_chat(**request_params):
                    yield event
            else:
                async for event in self._non_stream_chat(**request_params):
                    yield event

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            yield {"type": "error", "data": {"error": str(e), "provider": "anthropic"}}

    async def _stream_chat(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from Anthropic.

        Yields:
            Event dictionaries
        """
        async with self.client.messages.stream(**params) as stream:
            async for event in stream:
                if event.type == "message_start":
                    # Message started
                    yield {
                        "type": "message_start",
                        "data": {
                            "model": event.message.model,
                            "role": event.message.role,
                        },
                    }

                elif event.type == "content_block_start":
                    # New content block starting
                    if hasattr(event, "content_block"):
                        block = event.content_block
                        if isinstance(block, ToolUseBlock):
                            yield {
                                "type": "tool_call_start",
                                "data": {
                                    "id": block.id,
                                    "name": block.name,
                                    "index": event.index,
                                },
                            }

                elif event.type == "content_block_delta":
                    # Delta update to a content block
                    delta = event.delta
                    if hasattr(delta, "text"):
                        # Text content delta
                        yield {
                            "type": "content",
                            "data": {"text": delta.text, "index": event.index},
                        }
                    elif hasattr(delta, "partial_json"):
                        # Tool use input delta
                        yield {
                            "type": "tool_call_delta",
                            "data": {
                                "partial_json": delta.partial_json,
                                "index": event.index,
                            },
                        }

                elif event.type == "content_block_stop":
                    # Content block complete
                    yield {"type": "content_block_stop", "data": {"index": event.index}}

                elif event.type == "message_delta":
                    # Message metadata delta (e.g., stop_reason)
                    if hasattr(event, "delta") and hasattr(event.delta, "stop_reason"):
                        if event.delta.stop_reason:
                            yield {
                                "type": "stop",
                                "data": {"stop_reason": event.delta.stop_reason},
                            }

                elif event.type == "message_stop":
                    # Message complete
                    yield {"type": "done", "data": {"provider": "anthropic"}}

            # Get final message for usage stats
            final_message = await stream.get_final_message()
            if final_message.usage:
                yield {
                    "type": "usage",
                    "data": {
                        "input_tokens": final_message.usage.input_tokens,
                        "output_tokens": final_message.usage.output_tokens,
                    },
                }

    async def _non_stream_chat(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        """Non-streaming chat completion from Anthropic.

        Yields:
            Event dictionaries (yielded all at once)
        """
        response: Message = await self.client.messages.create(**params)

        yield {
            "type": "message_start",
            "data": {"model": response.model, "role": response.role},
        }

        # Process content blocks
        for idx, block in enumerate(response.content):
            if isinstance(block, TextBlock):
                yield {"type": "content", "data": {"text": block.text, "index": idx}}
            elif isinstance(block, ToolUseBlock):
                yield {
                    "type": "tool_call",
                    "data": {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                        "index": idx,
                    },
                }

        # Stop reason
        if response.stop_reason:
            yield {"type": "stop", "data": {"stop_reason": response.stop_reason}}

        # Usage stats
        if response.usage:
            yield {
                "type": "usage",
                "data": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
            }

        yield {"type": "done", "data": {"provider": "anthropic"}}
