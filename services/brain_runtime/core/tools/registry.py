"""Central tool registry for chat and agent modes."""

from typing import Dict, List, Optional, Any, Callable, Awaitable
from pydantic import BaseModel, Field
from functools import wraps
import logging

from core.errors import ToolError

logger = logging.getLogger(__name__)


class Tool(BaseModel):
    """A tool that can be called by an LLM."""

    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Human-readable description for LLM")
    parameters: dict = Field(..., description="JSON Schema for tool parameters")
    execute_fn: Optional[Callable] = Field(
        None, exclude=True, description="Async function to execute"
    )

    class Config:
        arbitrary_types_allowed = True

    def to_anthropic_format(self) -> dict:
        """Convert to Anthropic tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def to_openai_format(self) -> dict:
        """Convert to OpenAI function format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Central registry for all chat tools."""

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get singleton instance of registry."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (useful for testing)."""
        cls._instance = None

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_tools_for_provider(self, provider: str) -> List[Dict]:
        """
        Get tools formatted for a specific provider.

        Args:
            provider: "anthropic" or "openai"

        Returns:
            List of tool definitions in provider format
        """
        tools = []
        for tool in self._tools.values():
            if provider == "anthropic":
                tools.append(tool.to_anthropic_format())
            elif provider == "openai":
                tools.append(tool.to_openai_format())
            else:
                raise ToolError(f"Unknown provider: {provider}")
        return tools

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ToolError: If tool not found or execution fails
        """
        tool = self.get_tool(name)
        if not tool:
            raise ToolError(f"Tool not found: {name}")

        if not tool.execute_fn:
            raise ToolError(f"Tool {name} has no execute function")

        try:
            logger.info(f"Executing tool: {name} with args: {arguments}")
            result = await tool.execute_fn(**arguments)
            logger.info(f"Tool {name} completed successfully")
            return result
        except ToolError:
            # Re-raise ToolError as-is
            raise
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}", exc_info=True)
            raise ToolError(f"Tool execution failed: {e}") from e


def tool(name: str, description: str, parameters: dict):
    """
    Decorator to register a function as a tool.

    Example:
        @tool(
            name="get_today_events",
            description="Get calendar events for today",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
        async def get_today_events():
            # implementation
            pass
    """

    def decorator(func: Callable[..., Awaitable[Any]]):
        registry = ToolRegistry.get_instance()

        tool_obj = Tool(
            name=name, description=description, parameters=parameters, execute_fn=func
        )

        registry.register(tool_obj)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        return wrapper

    return decorator
