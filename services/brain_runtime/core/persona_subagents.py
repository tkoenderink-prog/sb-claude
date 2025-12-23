"""Factory for creating Claude SDK subagents from persona definitions."""

import logging
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession
from claude_agent_sdk import AgentDefinition

from models.db_models import ModeDB
from core.skill_loader import load_skills_for_persona, build_persona_system_prompt

logger = logging.getLogger(__name__)


async def create_all_persona_subagents(db: AsyncSession) -> Dict[str, AgentDefinition]:
    """Create AgentDefinition objects for all personas.

    These become available to the main agent via the Task tool.
    When the main agent calls Task(agent_name="socratic", task="..."),
    the SDK spawns the corresponding subagent with its system prompt and tools.

    Args:
        db: Database session

    Returns:
        Dict mapping persona name (lowercase) to AgentDefinition
    """
    from core.council import get_all_personas

    subagents = {}
    personas = await get_all_personas(db)

    logger.info(f"Creating subagents for {len(personas)} personas")

    for persona in personas:
        # Load persona's exclusive skills
        skills = await load_skills_for_persona(str(persona.id), db)

        # Build complete system prompt
        system_prompt = build_persona_system_prompt(
            base_prompt="",
            persona=persona,
            skills=skills,
        )

        # Add subagent-specific instructions
        subagent_prompt = f"""{system_prompt}

## Subagent Role

You are operating as a subagent in a council consultation.
The orchestrator will call you via the Task tool when your perspective is needed.

When invoked:
1. Read the task/question carefully
2. Use your available tools to gather context (vault_search, calendar_read, etc.)
3. Apply your persona's reasoning style
4. Provide specific, cited findings
5. Be thorough but concise

You have full autonomy to use tools and explore. Reference specific findings
(e.g., "Your January 2025 note says..." or "Calendar shows 3 conflicts in week of...").
"""

        # Create subagent definition
        agent_def = AgentDefinition(
            name=persona.name.lower(),  # "socratic", "contrarian", etc.
            description=f"{persona.name}: {persona.description}",
            prompt=subagent_prompt,
            model="claude-sonnet-4-5-20250929",  # Sonnet for depth + tool use
        )

        subagents[persona.name.lower()] = agent_def
        logger.info(f"Created subagent: {persona.name.lower()}")

    return subagents


async def create_persona_subagent(
    persona: ModeDB,
    db: AsyncSession,
) -> AgentDefinition:
    """Create a single persona subagent.

    Useful for testing or selective subagent creation.

    Args:
        persona: Persona mode definition
        db: Database session

    Returns:
        AgentDefinition for this persona
    """
    skills = await load_skills_for_persona(str(persona.id), db)
    system_prompt = build_persona_system_prompt("", persona, skills)

    return AgentDefinition(
        name=persona.name.lower(),
        description=f"{persona.name}: {persona.description}",
        prompt=system_prompt,
        model="claude-sonnet-4-5-20250929",
    )
