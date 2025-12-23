"""Agent runtime for autonomous multi-step tasks."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional, List, Dict, Any
from anthropic import Anthropic

from core.tools.registry import ToolRegistry
from models.chat import ArtifactRef


class ArtifactManager:
    """Manages artifact creation and storage."""

    def __init__(self, storage_path: Path = Path("data/artifacts")):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def create(
        self,
        name: str,
        content: str,
        artifact_type: str = "report",
        mime_type: str = "text/markdown",
    ) -> ArtifactRef:
        """Create and store an artifact."""
        artifact_id = str(uuid.uuid4())
        path = self.storage_path / f"{artifact_id}.md"
        path.write_text(content)

        return ArtifactRef(
            id=artifact_id,
            name=name,
            type=artifact_type,
            mime_type=mime_type,
            size_bytes=len(content.encode()),
            download_url=f"/agent/runs/artifacts/{artifact_id}",
            created_at=datetime.now(timezone.utc),
        )

    def get_artifact_path(self, artifact_id: str) -> Optional[Path]:
        """Get the file path for an artifact."""
        path = self.storage_path / f"{artifact_id}.md"
        return path if path.exists() else None


class AgentRuntime:
    """Claude Agent SDK wrapper for autonomous tasks."""

    def __init__(self):
        from core.config import get_settings

        settings = get_settings()
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.tool_registry = ToolRegistry.get_instance()
        self.artifact_manager = ArtifactManager()

    async def run(
        self,
        task: str,
        context: Optional[str] = None,
        tools: Optional[List[str]] = None,
        max_turns: int = 10,
        attached_skills: List[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Run agent task with streaming.

        Args:
            task: The task description for the agent
            context: Optional additional context
            tools: Optional list of tool names to make available (None = all tools)
            max_turns: Maximum number of conversation turns
            attached_skills: List of skill IDs to attach to the agent

        Yields:
            Events with type and data describing agent progress
        """

        # Build system prompt with attached skills
        system_prompt = await self._build_system_prompt(attached_skills or [])

        # Get tools
        available_tools = self._get_tools(tools)

        # Initialize tracking
        run_id = str(uuid.uuid4())
        turns = 0
        total_tool_calls = 0
        input_tokens = 0
        output_tokens = 0
        artifacts = []

        # Build initial message
        user_message = task
        if context:
            user_message = f"{task}\n\nContext:\n{context}"

        messages = [{"role": "user", "content": user_message}]

        yield {"type": "status", "data": {"run_id": run_id, "status": "running"}}

        # Agent loop - continue until we hit max_turns or get end_turn
        for turn in range(max_turns):
            turns += 1

            # Call Claude
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=system_prompt,
                tools=available_tools,
                messages=messages,
            )

            # Track token usage
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens

            # Process response content
            assistant_content = []
            for block in response.content:
                if block.type == "text":
                    yield {"type": "text", "data": block.text}
                    assistant_content.append(block)
                elif block.type == "tool_use":
                    total_tool_calls += 1
                    yield {
                        "type": "tool_call",
                        "data": {
                            "id": block.id,
                            "tool": block.name,
                            "arguments": block.input,
                        },
                    }
                    assistant_content.append(block)

            # Add assistant message to conversation
            messages.append({"role": "assistant", "content": assistant_content})

            # Check if done (no more tool calls needed)
            if response.stop_reason == "end_turn":
                break

            # Execute tools if needed
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        # Execute the tool
                        result = await self.tool_registry.execute(
                            block.name, block.input
                        )

                        # Format result for API
                        result_content = (
                            json.dumps(result)
                            if not isinstance(result, str)
                            else result
                        )
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result_content,
                            }
                        )

                        # Yield event for streaming
                        yield {
                            "type": "tool_result",
                            "data": {"tool_call_id": block.id, "result": result},
                        }

                # Add tool results as user message to continue conversation
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason - break out
                break

        # Calculate cost (pricing as of Jan 2025 for Claude Sonnet 4)
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000

        yield {
            "type": "usage",
            "data": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "estimated_cost_usd": cost,
            },
        }

        yield {
            "type": "done",
            "data": {
                "run_id": run_id,
                "turns": turns,
                "tool_calls": total_tool_calls,
                "artifacts": [a.model_dump() for a in artifacts],
            },
        }

    async def _build_system_prompt(self, attached_skills: List[str]) -> str:
        """Build system prompt with optional attached skills."""
        base = """You are an AI assistant with access to the user's Second Brain system.
You can query their calendar, tasks, and knowledge vault to help with analysis and planning.

When executing multi-step tasks:
1. Break down complex tasks into clear steps
2. Use available tools to gather information
3. Synthesize findings into actionable insights
4. Provide clear reasoning for your decisions"""

        if not attached_skills:
            return base

        # Load skill content
        skill_content = []
        for skill_id in attached_skills:
            try:
                skill = await self.tool_registry.execute(
                    "get_skill", {"skill_id": skill_id}
                )
                if skill:
                    skill_content.append(
                        f"## Skill: {skill.get('name', skill_id)}\n\n{skill.get('content', '')}"
                    )
            except Exception:
                # Skip skills that fail to load
                continue

        if skill_content:
            return f"{base}\n\n# Attached Skills\n\n" + "\n\n".join(skill_content)
        return base

    def _get_tools(self, tool_names: Optional[List[str]]) -> List[Dict]:
        """Get tool definitions for the agent.

        Args:
            tool_names: Optional list of specific tool names, or None for all tools

        Returns:
            List of tool definitions in Anthropic format
        """
        all_tools = self.tool_registry.get_tools_for_provider("anthropic")
        if tool_names is None:
            return all_tools
        return [t for t in all_tools if t["name"] in tool_names]
