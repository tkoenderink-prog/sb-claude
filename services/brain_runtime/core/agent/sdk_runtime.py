"""Claude Agent SDK runtime for autonomous tasks.

This module provides the SDKAgentRuntime class that uses the official
Claude Agent SDK for agent execution with subagent support.
"""

import logging
from datetime import datetime
from typing import Optional, AsyncGenerator, Dict, Any

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    ResultMessage,
)

from core.tools.registry import ToolRegistry
from .mcp_tools import get_brain_tools_for_sdk

logger = logging.getLogger(__name__)


class SDKAgentRuntime:
    """Runtime for executing autonomous agent tasks using Claude Agent SDK."""

    def __init__(self, api_key: str):
        """Initialize SDK agent runtime.

        Args:
            api_key: Anthropic API key for Claude
        """
        self.api_key = api_key
        self.tool_registry = ToolRegistry.get_instance()

        # Define standard subagents using AgentDefinition class
        self.subagents = {
            "calendar_analyst": AgentDefinition(
                description="Analyzes calendar schedules, detects conflicts, and provides time management insights",
                prompt="""You are a calendar analysis specialist.

Your role:
- Analyze calendar events for patterns and conflicts
- Identify scheduling issues and optimization opportunities
- Provide time management recommendations
- Detect overcommitment and suggest adjustments

Be thorough and cite specific events when making observations.""",
                tools=[
                    "get_today_events",
                    "get_week_events",
                    "get_events_in_range",
                    "search_events",
                ],
                model="haiku",  # Cost-efficient for focused analysis
            ),
            "task_analyst": AgentDefinition(
                description="Analyzes tasks, identifies priorities and blockers, and suggests action plans",
                prompt="""You are a task management and prioritization specialist.

Your role:
- Analyze task lists for priorities and dependencies
- Identify blockers and suggest workarounds
- Recommend task sequencing and time allocation
- Highlight overdue items and urgent actions

Be actionable and specific in your recommendations.""",
                tools=[
                    "get_overdue_tasks",
                    "get_today_tasks",
                    "query_tasks",
                    "get_tasks_by_project",
                ],
                model="haiku",  # Cost-efficient for task analysis
            ),
            "knowledge_searcher": AgentDefinition(
                description="Deep vault research specialist for finding and synthesizing information from notes",
                prompt="""You are a knowledge vault research specialist.

Your role:
- Search the vault for relevant information
- Synthesize findings from multiple sources
- Identify connections between notes
- Provide well-cited, comprehensive answers

Always cite sources and provide file paths for key information.""",
                tools=[
                    "semantic_search",
                    "text_search",
                    "read_vault_file",
                    "list_vault_directory",
                ],
                model="haiku",  # Cost-efficient for search and synthesis
            ),
        }
        # NOTE: Persona subagents (socratic, contrarian, etc.) are loaded dynamically
        # in execute() method via create_all_persona_subagents() for council support

    async def execute(
        self,
        run_id: str,
        task: str,
        context: Optional[str] = None,
        tools: Optional[list[str]] = None,
        max_turns: int = 10,
        attached_skills: list[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute autonomous agent task using Claude Agent SDK.

        Args:
            run_id: Unique run identifier
            task: Task description for the agent
            context: Optional additional context
            tools: Optional list of specific tool names (None = all tools)
            max_turns: Maximum conversation turns (not used by SDK directly)
            attached_skills: Skills to include in system prompt

        Yields:
            Events with type and data describing agent progress
        """
        logger.info(f"Starting SDK agent run {run_id}: {task[:100]}...")

        # Build system prompt with skills and subagent info
        system_prompt = await self._build_system_prompt(attached_skills or [])

        # Build user message with context
        user_message = task
        if context:
            user_message = f"{task}\n\nAdditional Context:\n{context}"

        # Get available tools (SDK format)
        available_tools = get_brain_tools_for_sdk()

        # Filter tools if specific ones requested
        if tools is not None:
            available_tools = [t for t in available_tools if t["name"] in tools]

        # Load persona subagents for council support
        from core.database import get_session_factory
        from core.persona_subagents import create_all_persona_subagents

        async with get_session_factory()() as db:
            persona_subagents = await create_all_persona_subagents(db)
            # Merge persona subagents with standard subagents
            all_subagents = {**self.subagents, **persona_subagents}
            logger.info(f"Loaded {len(persona_subagents)} persona subagents for councils")

        # Get tool names for allowed_tools (required for SDK)
        # IMPORTANT: Include "Task" and "query_persona_with_provider" for councils
        tool_names = [t["name"] for t in available_tools]
        allowed_tools = tool_names + ["Task", "query_persona_with_provider"]

        logger.info(f"Agent has access to {len(tool_names)} tools + Task + query_persona_with_provider")

        # Create SDK options with all subagents (standard + persona)
        options = ClaudeAgentOptions(
            api_key=self.api_key,
            model="claude-sonnet-4-5-20250929",  # Sonnet 4.5 for orchestration
            max_tokens=4096,
            allowed_tools=allowed_tools,
            agents=all_subagents,  # Enable subagent delegation (includes persona subagents)
        )

        # Track metrics
        turns = 0
        total_tool_calls = 0
        input_tokens = 0
        output_tokens = 0

        # Emit start status
        yield {
            "type": "status",
            "data": {"run_id": run_id, "status": "running", "turns": 0},
        }

        try:
            # Use SDK's query function for streaming execution
            async for message in query(
                prompt=user_message,
                system=system_prompt,
                options=options,
            ):
                # Handle different message types using isinstance pattern
                if isinstance(message, AssistantMessage):
                    turns += 1

                    # Process content blocks
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            # Stream text to client
                            yield {"type": "text", "data": block.text}

                        elif isinstance(block, ToolUseBlock):
                            # Tool call detected
                            total_tool_calls += 1
                            yield {
                                "type": "tool_call",
                                "data": {
                                    "id": block.id,
                                    "tool": block.name,
                                    "arguments": block.input,
                                },
                            }

                        elif isinstance(block, ToolResultBlock):
                            # Tool result from SDK
                            yield {
                                "type": "tool_result",
                                "data": {
                                    "tool_call_id": block.tool_use_id,
                                    "result": block.content,
                                },
                            }

                    # Track token usage if available
                    if hasattr(message, "usage") and message.usage:
                        input_tokens += getattr(message.usage, "input_tokens", 0)
                        output_tokens += getattr(message.usage, "output_tokens", 0)

                elif isinstance(message, ResultMessage):
                    # Final result from SDK
                    logger.info(f"Agent run {run_id} completed")

                    # Extract final token usage
                    if hasattr(message, "usage") and message.usage:
                        input_tokens = getattr(message.usage, "input_tokens", 0)
                        output_tokens = getattr(message.usage, "output_tokens", 0)

                    # Emit usage
                    cost = self._estimate_cost(input_tokens, output_tokens)
                    yield {
                        "type": "usage",
                        "data": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens,
                            "total_tokens": input_tokens + output_tokens,
                            "estimated_cost_usd": cost,
                        },
                    }

                    # Emit done status
                    yield {
                        "type": "done",
                        "data": {
                            "run_id": run_id,
                            "turns": turns,
                            "tool_calls": total_tool_calls,
                        },
                    }

        except Exception as e:
            logger.error(f"SDK agent run {run_id} failed: {e}", exc_info=True)
            yield {
                "type": "error",
                "data": {"error": str(e), "run_id": run_id},
            }

    async def _build_system_prompt(self, attached_skills: list[str]) -> str:
        """Build system prompt with subagent descriptions and skills.

        Args:
            attached_skills: List of skill IDs to include

        Returns:
            System prompt string
        """
        # Base prompt with subagent descriptions
        today = datetime.now().strftime("%Y-%m-%d (%A)")
        prompt = f"""You are an autonomous AI agent with access to the user's Second Brain system.

Today's date: {today}

You can:
- Query calendar events and analyze schedules
- Review tasks and identify priorities
- Search the knowledge vault for information
- Delegate specialized tasks to subagents

# Available Subagents

You can delegate focused tasks to specialized subagents:

1. **calendar_analyst**: For calendar analysis, conflict detection, and time management
   - Use when: Analyzing schedules, finding conflicts, optimizing time allocation
   - Tools: Calendar event queries and search

2. **task_analyst**: For task prioritization, blocker identification, and action planning
   - Use when: Analyzing task lists, identifying urgent items, planning work sequences
   - Tools: Task queries and filtering

3. **knowledge_searcher**: For deep vault research and information synthesis
   - Use when: Finding specific information, connecting related notes, comprehensive research
   - Tools: Semantic search, text search, file reading

Delegate to subagents when you need focused expertise. Otherwise, use tools directly for straightforward queries.

# Your Approach

For complex tasks:
1. Break down the task into clear steps
2. Delegate specialized subtasks to appropriate subagents
3. Use tools directly for simple queries
4. Synthesize findings into coherent insights
5. Provide clear reasoning and cite sources
"""

        # Add attached skills if any
        if attached_skills:
            prompt += "\n\n# Attached Skills\n\n"
            prompt += "You have access to these additional skills and frameworks:\n\n"

            for skill_id in attached_skills:
                try:
                    # Load skill content via registry
                    skill = await self.tool_registry.execute(
                        "get_skill", {"skill_id": skill_id}
                    )
                    if skill:
                        skill_name = skill.get("name", skill_id)
                        skill_content = skill.get("content", "")
                        prompt += f"## {skill_name}\n\n{skill_content}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to load skill {skill_id}: {e}")
                    continue

        return prompt

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost in USD for Claude Sonnet 4.5.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Claude Sonnet 4.5 pricing (December 2025)
        # $3 per million input tokens, $15 per million output tokens
        input_cost = (input_tokens / 1_000_000) * 3.0
        output_cost = (output_tokens / 1_000_000) * 15.0
        return input_cost + output_cost
