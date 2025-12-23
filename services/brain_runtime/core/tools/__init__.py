"""Tool registry system for chat and agent modes."""

from .registry import ToolRegistry, Tool, tool
from .executor import ToolExecutor, ToolCallRequest, ToolCallResult
from .calendar_tools import register_calendar_tools
from .tasks_tools import register_tasks_tools
from .vault_tools import register_vault_tools
from .skills_tools import register_skills_tools
from .proposal_tools import register_proposal_tools
from .persona_query import query_persona_with_provider  # Auto-registers via @tool decorator
from core.errors import ToolError

__all__ = [
    "ToolRegistry",
    "Tool",
    "tool",
    "ToolError",
    "ToolExecutor",
    "ToolCallRequest",
    "ToolCallResult",
    "register_calendar_tools",
    "register_tasks_tools",
    "register_vault_tools",
    "register_skills_tools",
    "register_proposal_tools",
    "query_persona_with_provider",
]


def register_all_tools() -> int:
    """Register all available tools in the registry.

    Returns:
        Number of tools registered.
    """
    register_calendar_tools()
    register_tasks_tools()
    register_vault_tools()
    register_skills_tools()
    register_proposal_tools()
    # persona_query tool auto-registers via @tool decorator

    registry = ToolRegistry.get_instance()
    return len(registry.get_all_tools())
