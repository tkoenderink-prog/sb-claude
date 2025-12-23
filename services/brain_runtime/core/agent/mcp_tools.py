"""MCP tool wrappers for Claude Agent SDK.

This module wraps all brain tools as MCP tools using the official Claude Agent SDK.
"""

import logging
from claude_agent_sdk import create_sdk_mcp_server, tool
from core.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def create_mcp_server() -> object:
    """Create MCP server with all brain tools wrapped.

    This function wraps all tools from the ToolRegistry as MCP tools
    using the Claude Agent SDK's @tool decorator pattern.

    Returns:
        MCP server instance with all tools registered
    """
    registry = ToolRegistry.get_instance()

    # Get all tools from registry
    all_tools = registry.get_all_tools()

    logger.info(f"Creating MCP server with {len(all_tools)} tools")

    # Create wrapped tool functions
    wrapped_tools = []

    for brain_tool in all_tools:
        # Create a wrapped async function for each tool
        # We need to do this dynamically since we don't know the tools at import time
        async def make_tool_wrapper(tool_instance):
            """Factory to create tool wrapper with proper closure."""
            tool_name = tool_instance.name
            tool_execute = tool_instance.execute_fn

            async def wrapper(**kwargs):
                """Wrapper that executes the brain tool."""
                logger.info(f"MCP tool called: {tool_name}")
                try:
                    result = await tool_execute(**kwargs)
                    return result
                except Exception as e:
                    logger.error(f"MCP tool {tool_name} failed: {e}", exc_info=True)
                    raise

            # Set function metadata for SDK
            wrapper.__name__ = tool_name
            wrapper.__doc__ = tool_instance.description

            return wrapper

        # Create the wrapper (note: we can't await here, so we use sync approach)
        # Instead, we'll use a different approach - create functions on the fly
        def create_wrapper(tool_inst):
            """Create wrapper function for a tool."""
            async def tool_func(**kwargs):
                return await registry.execute(tool_inst.name, kwargs)

            tool_func.__name__ = tool_inst.name
            tool_func.__doc__ = tool_inst.description

            # Decorate with @tool from SDK
            decorated = tool(
                name=tool_inst.name,
                description=tool_inst.description,
                parameters=tool_inst.parameters
            )(tool_func)

            return decorated

        wrapped_tool = create_wrapper(brain_tool)
        wrapped_tools.append(wrapped_tool)
        logger.info(f"Wrapped MCP tool: {brain_tool.name}")

    # Create MCP server with all wrapped tools
    mcp_server = create_sdk_mcp_server(tools=wrapped_tools)

    logger.info(f"MCP server created with {len(wrapped_tools)} tools")

    return mcp_server


def get_brain_tool_names() -> list[str]:
    """Get list of all brain tool names available.

    Returns:
        List of tool names from the registry
    """
    registry = ToolRegistry.get_instance()
    return [tool.name for tool in registry.get_all_tools()]


def get_brain_tools_for_sdk() -> list[dict]:
    """Get brain tools formatted for Claude Agent SDK.

    Returns:
        List of tool definitions in Anthropic format (SDK compatible)
    """
    registry = ToolRegistry.get_instance()
    return registry.get_tools_for_provider("anthropic")
