"""Tool execution engine for chat and agent modes."""

import json
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .registry import ToolRegistry


def json_serializer(obj: Any) -> str:
    """Custom JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRequest:
    """Request to execute a tool."""

    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ToolCallResult:
    """Result from a tool execution."""

    tool_call_id: str
    success: bool
    content: Any
    error: Optional[str] = None


class ToolExecutor:
    """Executes tools and formats results for LLM providers."""

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize tool executor.

        Args:
            registry: Tool registry instance (defaults to singleton)
        """
        self.registry = registry or ToolRegistry.get_instance()

    async def execute(self, tool_call: ToolCallRequest) -> ToolCallResult:
        """
        Execute a single tool call with error handling.

        Args:
            tool_call: Tool call request

        Returns:
            Tool call result with success/error status
        """
        try:
            logger.info(f"Executing tool: {tool_call.name} (id={tool_call.id})")
            logger.debug(f"Tool arguments: {tool_call.arguments}")

            # Execute tool via registry
            result = await self.registry.execute(tool_call.name, tool_call.arguments)

            logger.info(f"Tool {tool_call.name} executed successfully")
            return ToolCallResult(
                tool_call_id=tool_call.id, success=True, content=result, error=None
            )

        except ValueError as e:
            # Tool not found or validation error
            logger.error(f"Tool validation error for {tool_call.name}: {e}")
            return ToolCallResult(
                tool_call_id=tool_call.id,
                success=False,
                content=None,
                error=f"Tool validation error: {str(e)}",
            )

        except Exception as e:
            # Execution error
            logger.error(f"Tool execution failed for {tool_call.name}: {e}", exc_info=True)
            return ToolCallResult(
                tool_call_id=tool_call.id,
                success=False,
                content=None,
                error=f"Tool execution failed: {str(e)}",
            )

    async def execute_all(
        self, tool_calls: List[ToolCallRequest]
    ) -> List[ToolCallResult]:
        """
        Execute multiple tool calls in sequence.

        Args:
            tool_calls: List of tool call requests

        Returns:
            List of tool call results (same order as input)
        """
        results = []
        for tool_call in tool_calls:
            result = await self.execute(tool_call)
            results.append(result)
        return results

    def format_for_anthropic(
        self, results: List[ToolCallResult]
    ) -> List[Dict[str, Any]]:
        """
        Format tool results for Anthropic API.

        Anthropic expects tool results as content blocks in a user message:
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "...",
                    "content": "..." or [{"type": "text", "text": "..."}]
                }
            ]
        }

        Args:
            results: List of tool call results

        Returns:
            List of content blocks for Anthropic API
        """
        content_blocks = []
        for result in results:
            # Format content
            if result.success:
                # Success - include the result content
                # Convert to string if it's a complex object
                if isinstance(result.content, (dict, list)):
                    content_str = json.dumps(
                        result.content, indent=2, default=json_serializer
                    )
                else:
                    content_str = str(result.content)

                content_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_call_id,
                        "content": content_str,
                    }
                )
            else:
                # Error - include error message with is_error flag
                content_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_call_id,
                        "content": result.error or "Unknown error",
                        "is_error": True,
                    }
                )

        return content_blocks

    def format_for_openai(self, results: List[ToolCallResult]) -> List[Dict[str, Any]]:
        """
        Format tool results for OpenAI API.

        OpenAI expects tool results as separate messages with role "tool":
        {
            "role": "tool",
            "tool_call_id": "...",
            "content": "..."
        }

        Args:
            results: List of tool call results

        Returns:
            List of tool result messages for OpenAI API
        """
        messages = []
        for result in results:
            # Format content
            if result.success:
                # Success - include the result content
                if isinstance(result.content, (dict, list)):
                    content_str = json.dumps(
                        result.content, indent=2, default=json_serializer
                    )
                else:
                    content_str = str(result.content)
            else:
                # Error - include error message
                content_str = f"Error: {result.error or 'Unknown error'}"

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": result.tool_call_id,
                    "content": content_str,
                }
            )

        return messages
