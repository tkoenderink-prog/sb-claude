"""Persona query tool for multi-provider council execution."""

import logging
from litellm import acompletion

from .registry import tool

logger = logging.getLogger(__name__)


@tool(
    name="query_persona_with_provider",
    description="""Query a specific persona using a specific LLM provider.

Use this to get perspectives from different AI architectures:
- anthropic: Claude (nuanced reasoning, careful analysis)
- openai: GPT (broad knowledge, comprehensive coverage)
- google: Gemini (fast, efficient insights)

Each persona has their own system prompt and exclusive skills that shape their response.

Example usage in a council:
query_persona_with_provider(
    persona_name="Socratic",
    provider="anthropic",
    query="Should I take this new job offer?"
)

Returns the persona's perspective as a string.""",
    parameters={
        "type": "object",
        "properties": {
            "persona_name": {
                "type": "string",
                "description": "Name of the persona (Socratic, Contrarian, Pragmatist, Synthesizer, Coach)",
            },
            "provider": {
                "type": "string",
                "enum": ["anthropic", "openai", "google"],
                "description": "LLM provider to use for this query",
            },
            "query": {
                "type": "string",
                "description": "The question or situation to present to the persona",
            },
        },
        "required": ["persona_name", "provider", "query"],
    },
)
async def query_persona_with_provider(
    persona_name: str,
    provider: str,
    query: str,
) -> str:
    """Query a persona using a specific LLM provider.

    This tool enables fast councils where different AI models provide
    perspectives through different persona lenses.

    Args:
        persona_name: Name of persona (case-insensitive)
        provider: LLM provider (anthropic, openai, google)
        query: Question to ask the persona

    Returns:
        Persona's response as a string
    """
    from core.council import get_persona_by_name
    from core.skill_loader import load_skills_for_persona, build_persona_system_prompt
    from core.database import get_session_factory

    logger.info(f"Querying {persona_name} via {provider}")

    async with get_session_factory()() as db:
        # Load persona
        persona = await get_persona_by_name(persona_name, db)
        if not persona:
            error_msg = f"Persona '{persona_name}' not found. Available: Socratic, Contrarian, Pragmatist, Synthesizer, Coach"
            logger.error(error_msg)
            return f"[Error: {error_msg}]"

        # Load persona's exclusive skills
        skills = await load_skills_for_persona(str(persona.id), db)
        logger.info(f"Loaded {len(skills)} skills for {persona_name}")

        # Build complete system prompt (persona + skills)
        system_prompt = build_persona_system_prompt(
            base_prompt="",
            persona=persona,
            skills=skills,
        )

        # Map provider to model
        PROVIDER_MODELS = {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-4o-mini",
            "google": "gemini/gemini-2.0-flash-exp",
        }

        model = PROVIDER_MODELS.get(provider)
        if not model:
            error_msg = f"Unknown provider '{provider}'. Use: anthropic, openai, or google"
            logger.error(error_msg)
            return f"[Error: {error_msg}]"

        # Query via LiteLLM
        try:
            logger.info(f"Calling {model} for {persona_name}")

            response = await acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                max_tokens=300,
                temperature=0.7,
            )

            result = response.choices[0].message.content
            logger.info(f"{persona_name} responded with {len(result)} chars")

            return result

        except Exception as e:
            error_msg = f"Error querying {provider}: {str(e)}"
            logger.error(error_msg)
            return f"[{error_msg}]"


def register_persona_query_tool():
    """Register persona query tool (called by decorator)."""
    logger.info("Persona query tool registered")
