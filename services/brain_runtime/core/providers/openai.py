"""OpenAI GPT provider implementation."""

import logging
import json
from typing import AsyncGenerator, List, Optional, Dict, Any
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion

from .base import BaseProvider, ProviderModel, ModelCapability

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseProvider):
    """Provider implementation for OpenAI GPT."""

    # Available models
    MODELS = [
        ProviderModel(
            id="gpt-4-turbo",
            name="GPT-4 Turbo",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
            ],
            context_window=128000,
            max_output=4096,
        ),
        ProviderModel(
            id="gpt-4o",
            name="GPT-4o",
            capabilities=[
                ModelCapability.TOOLS,
                ModelCapability.VISION,
                ModelCapability.STREAMING,
            ],
            context_window=128000,
            max_output=16384,
        ),
        ProviderModel(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            capabilities=[ModelCapability.TOOLS, ModelCapability.STREAMING],
            context_window=128000,
            max_output=16384,
        ),
    ]

    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, api_key: str):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
        """
        super().__init__(api_key)
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def name(self) -> str:
        """Get provider name."""
        return "openai"

    def get_default_model(self) -> str:
        """Get default model ID."""
        return self.DEFAULT_MODEL

    def supports_tools(self) -> bool:
        """OpenAI supports function calling."""
        return True

    def get_models(self) -> List[ProviderModel]:
        """Get available OpenAI models."""
        return self.MODELS

    def format_tools(self, tools: List[Dict]) -> List[Dict]:
        """Format tools for OpenAI API.

        OpenAI expects:
        {
            "type": "function",
            "function": {
                "name": "tool_name",
                "description": "Tool description",
                "parameters": {
                    "type": "object",
                    "properties": {...},
                    "required": [...]
                }
            }
        }

        Args:
            tools: List of tool definitions in standard format

        Returns:
            List of tools formatted for OpenAI
        """
        formatted = []
        for tool in tools:
            formatted.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get(
                            "parameters",
                            {"type": "object", "properties": {}, "required": []},
                        ),
                    },
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
        """Send chat request to OpenAI and stream response.

        Args:
            messages: List of messages in OpenAI format
            tools: Optional list of available tools
            stream: Whether to stream the response
            model: Model ID (defaults to gpt-4o)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Yields:
            Event dictionaries
        """
        # Default parameters
        model_id = model or self.DEFAULT_MODEL
        temperature = temperature if temperature is not None else 1.0

        # Build request parameters
        request_params = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            request_params["max_tokens"] = max_tokens

        if tools:
            request_params["tools"] = self.format_tools(tools)
            request_params["tool_choice"] = "auto"

        try:
            if stream:
                async for event in self._stream_chat(**request_params):
                    yield event
            else:
                async for event in self._non_stream_chat(**request_params):
                    yield event

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            yield {"type": "error", "data": {"error": str(e), "provider": "openai"}}

    async def _stream_chat(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion from OpenAI.

        Yields:
            Event dictionaries
        """
        # Track tool calls being built up across chunks
        tool_calls = {}
        message_started = False

        stream = await self.client.chat.completions.create(**params)

        async for chunk in stream:
            if not chunk.choices:
                continue

            choice = chunk.choices[0]

            # Message start
            if not message_started:
                yield {
                    "type": "message_start",
                    "data": {"model": chunk.model, "role": "assistant"},
                }
                message_started = True

            # Content delta
            if choice.delta.content:
                yield {
                    "type": "content",
                    "data": {"text": choice.delta.content, "index": choice.index},
                }

            # Tool call deltas
            if choice.delta.tool_calls:
                for tool_call_delta in choice.delta.tool_calls:
                    idx = tool_call_delta.index

                    # Initialize tool call if first chunk
                    if idx not in tool_calls:
                        tool_calls[idx] = {
                            "id": tool_call_delta.id or "",
                            "name": "",
                            "arguments": "",
                        }

                        if tool_call_delta.function and tool_call_delta.function.name:
                            tool_calls[idx]["name"] = tool_call_delta.function.name
                            yield {
                                "type": "tool_call_start",
                                "data": {
                                    "id": tool_call_delta.id,
                                    "name": tool_call_delta.function.name,
                                    "index": idx,
                                },
                            }

                    # Accumulate arguments
                    if tool_call_delta.function and tool_call_delta.function.arguments:
                        tool_calls[idx][
                            "arguments"
                        ] += tool_call_delta.function.arguments
                        yield {
                            "type": "tool_call_delta",
                            "data": {
                                "partial_json": tool_call_delta.function.arguments,
                                "index": idx,
                            },
                        }

            # Finish reason
            if choice.finish_reason:
                # Yield complete tool calls
                for idx, tool_call in tool_calls.items():
                    try:
                        arguments = json.loads(tool_call["arguments"])
                    except json.JSONDecodeError:
                        arguments = {}

                    yield {
                        "type": "tool_call",
                        "data": {
                            "id": tool_call["id"],
                            "name": tool_call["name"],
                            "input": arguments,
                            "index": idx,
                        },
                    }

                yield {"type": "stop", "data": {"stop_reason": choice.finish_reason}}

        # OpenAI doesn't provide usage in streaming mode
        yield {"type": "done", "data": {"provider": "openai"}}

    async def _non_stream_chat(self, **params) -> AsyncGenerator[Dict[str, Any], None]:
        """Non-streaming chat completion from OpenAI.

        Yields:
            Event dictionaries (yielded all at once)
        """
        # Remove stream parameter for non-streaming
        params = {k: v for k, v in params.items() if k != "stream"}

        response: ChatCompletion = await self.client.chat.completions.create(**params)

        if not response.choices:
            yield {
                "type": "error",
                "data": {"error": "No choices in response", "provider": "openai"},
            }
            return

        choice = response.choices[0]
        message = choice.message

        yield {
            "type": "message_start",
            "data": {"model": response.model, "role": message.role},
        }

        # Content
        if message.content:
            yield {"type": "content", "data": {"text": message.content, "index": 0}}

        # Tool calls
        if message.tool_calls:
            for idx, tool_call in enumerate(message.tool_calls):
                try:
                    arguments = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    arguments = {}

                yield {
                    "type": "tool_call",
                    "data": {
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "input": arguments,
                        "index": idx,
                    },
                }

        # Finish reason
        if choice.finish_reason:
            yield {"type": "stop", "data": {"stop_reason": choice.finish_reason}}

        # Usage stats
        if response.usage:
            yield {
                "type": "usage",
                "data": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                },
            }

        yield {"type": "done", "data": {"provider": "openai"}}
