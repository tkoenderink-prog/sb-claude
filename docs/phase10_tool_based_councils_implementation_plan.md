# Phase 10: Tool-Based Councils - Complete Implementation Plan

**Date:** 2025-12-22
**Architecture:** Tool-Based (Skills as Instructions)
**Status:** READY FOR IMPLEMENTATION

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Component 1: Fast Councils (LiteLLM)](#component-1-fast-councils-litellm)
3. [Component 2: Deep Councils (SDK Subagents)](#component-2-deep-councils-sdk-subagents)
4. [Council Skill Definitions](#council-skill-definitions)
5. [Integration with Chat System](#integration-with-chat-system)
6. [Testing Strategy](#testing-strategy)
7. [Deployment & Migration](#deployment--migration)
8. [Usage Documentation](#usage-documentation)

---

## Architecture Overview

### Core Concept

**Council skills are natural language instructions that the LLM reads and executes using tools.**

```
User: "Should I take this job? Invoke Decision Council."
  ↓
Skill injection system loads Decision Council skill
  ↓
LLM reads skill content (instructions)
  ↓
LLM uses tools as instructed (query_persona_with_provider or Task)
  ↓
LLM synthesizes responses using template from skill
  ↓
Returns formatted council analysis
```

### Two Execution Paths

#### Fast Path (Multi-Provider via LiteLLM)
- **Tool:** `query_persona_with_provider(persona_name, provider, query)`
- **Purpose:** Get perspectives from different AI models (Claude, GPT, Gemini)
- **Speed:** ~3-5 seconds (parallel queries)
- **Cost:** ~$0.005 per council

#### Deep Path (SDK Subagents)
- **Tool:** `Task(agent_name, task)` (built into Claude SDK)
- **Purpose:** Tool-enabled research (vault_search, calendar_read)
- **Speed:** ~15-25 seconds (sequential with tools)
- **Cost:** ~$0.05-0.08 per council

### No Parsing Required

Council skills don't need special structure. They're freeform markdown that:
1. Explains when to use the council
2. Lists which tools to call
3. Provides synthesis template
4. LLM reads and follows

---

## Component 1: Fast Councils (LiteLLM)

### Tool Implementation

**File:** `services/brain_runtime/core/tools/persona_query.py`

```python
"""Persona query tool for multi-provider council execution."""

from typing import Optional
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
```

### LiteLLM Configuration

**File:** `services/brain_runtime/core/multi_llm.py` (extend existing)

```python
"""Multi-LLM client configuration for council providers."""

import os
from typing import Optional

# Provider configurations
PROVIDER_CONFIGS = {
    "anthropic": {
        "models": {
            "haiku": "claude-haiku-4-5-20251001",
            "sonnet": "claude-sonnet-4-5-20250929",
        },
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openai": {
        "models": {
            "mini": "gpt-4o-mini",
            "standard": "gpt-4o",
        },
        "env_key": "OPENAI_API_KEY",
    },
    "google": {
        "models": {
            "flash": "gemini/gemini-2.0-flash-exp",
            "pro": "gemini/gemini-1.5-pro",
        },
        "env_key": "GOOGLE_API_KEY",
    },
}


def get_available_providers() -> list[str]:
    """Get list of providers with valid API keys."""
    available = []
    for provider, config in PROVIDER_CONFIGS.items():
        if os.getenv(config["env_key"]):
            available.append(provider)
    return available


def validate_provider_setup() -> dict[str, bool]:
    """Check which providers are configured."""
    return {
        provider: bool(os.getenv(config["env_key"]))
        for provider, config in PROVIDER_CONFIGS.items()
    }
```

---

## Component 2: Deep Councils (SDK Subagents)

### Subagent Factory

**File:** `services/brain_runtime/core/persona_subagents.py` (NEW)

```python
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
```

### Council Helper Functions

**File:** `services/brain_runtime/core/council.py` (extend existing)

```python
"""Council-related helper functions."""

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import ModeDB, UserSkillDB


async def get_persona_by_name(persona_name: str, db: AsyncSession) -> Optional[ModeDB]:
    """Get a persona by name (case-insensitive)."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.name.ilike(persona_name),
            ModeDB.is_persona == True,
            ModeDB.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_all_personas(db: AsyncSession) -> List[ModeDB]:
    """Get all personas."""
    result = await db.execute(
        select(ModeDB)
        .where(ModeDB.is_persona == True, ModeDB.deleted_at.is_(None))
        .order_by(ModeDB.name)
    )
    return list(result.scalars().all())


async def get_council_skill_by_name(council_name: str, db: AsyncSession) -> Optional[UserSkillDB]:
    """Get a council skill by name."""
    result = await db.execute(
        select(UserSkillDB).where(
            UserSkillDB.name.ilike(council_name),
            UserSkillDB.category == "council",
            UserSkillDB.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()
```

---

## Component 3: Integration with Chat System

### Chat Endpoint Enhancement

**File:** `services/brain_runtime/api/chat.py` (modify existing)

```python
# Add to imports
from core.persona_subagents import create_all_persona_subagents

# In chat endpoint, when creating ClaudeAgentOptions:

async def chat_stream(request: ChatRequest, db: AsyncSession):
    """Stream chat responses with persona subagents available."""

    # ... existing setup ...

    # Create persona subagents for deep councils
    subagents = await create_all_persona_subagents(db)
    logger.info(f"Loaded {len(subagents)} persona subagents for councils")

    # Build options with subagents + all tools
    from core.tools.registry import ToolRegistry
    tool_registry = ToolRegistry.get_instance()

    options = ClaudeAgentOptions(
        model=request.model or "claude-sonnet-4-5-20250929",
        system_prompt=system_prompt,
        agents=subagents,  # Makes Task tool available with all personas
        allowed_tools=[
            "Task",  # For deep councils (spawn subagents)
            "query_persona_with_provider",  # For fast councils
            *tool_registry.get_tool_names(),  # All other tools
        ],
        max_tokens=8192,
    )

    # ... rest of chat logic ...
```

### Tool Registration

**File:** `services/brain_runtime/core/tools/registry.py` (ensure tool is registered)

```python
# The @tool decorator auto-registers, but verify in get_tools_for_provider():

def get_tools_for_provider(self, provider: str) -> List[dict]:
    """Get tools formatted for provider."""
    tools = []

    for tool_name, tool_def in self._tools.items():
        # Include query_persona_with_provider
        if tool_name == "query_persona_with_provider":
            tools.append({
                "name": tool_name,
                "description": tool_def["description"],
                "input_schema": tool_def["parameters"],
            })
        # ... other tools ...

    return tools
```

---

## Council Skill Definitions

### Example 1: Decision Council (Fast)

**SQL Insert:**

```sql
INSERT INTO user_skills (
    name,
    description,
    category,
    when_to_use,
    content,
    persona_ids
) VALUES (
    'Decision Council',
    'Multi-perspective decision analysis using different AI providers',
    'council',
    'When facing important decisions with significant consequences, multiple options, or high uncertainty',
    E'# Decision Council

Quick multi-perspective analysis from different AI architectures.

## When to Use

- Major life or career decisions
- Strategic choices with long-term implications
- Decisions where you feel stuck between options
- Situations with high uncertainty or risk
- When you notice yourself avoiding a decision

## How to Execute

When the user asks to invoke this council:

### Step 1: Query Three Personas with Different Providers

Use the **query_persona_with_provider** tool three times. You can call these in parallel for speed:

1. **Socratic perspective via Claude:**
   ```
   query_persona_with_provider(
       persona_name="Socratic",
       provider="anthropic",
       query="[user''s question]"
   )
   ```

2. **Contrarian perspective via GPT:**
   ```
   query_persona_with_provider(
       persona_name="Contrarian",
       provider="openai",
       query="[user''s question]"
   )
   ```

3. **Pragmatist perspective via Gemini:**
   ```
   query_persona_with_provider(
       persona_name="Pragmatist",
       provider="google",
       query="[user''s question]"
   )
   ```

### Step 2: Present All Three Responses

You will receive three different perspectives shaped by both:
- The persona''s reasoning style (Socratic questions, Contrarian critiques, Pragmatist actions)
- The AI model''s approach (Claude''s nuance, GPT''s breadth, Gemini''s efficiency)

### Step 3: Synthesize Using This Template

---

## Decision Analysis

**Question:** [Restate user''s decision]

### Perspectives

**Socratic (via Claude Haiku):**
[Insert Socratic response - expect questions and assumption probing]

**Contrarian (via GPT-4o-mini):**
[Insert Contrarian response - expect risk analysis and failure modes]

**Pragmatist (via Gemini Flash):**
[Insert Pragmatist response - expect action items and next steps]

---

### My Synthesis

**Consensus:**
[What all three perspectives agreed on - this is probably true/important]

**Key Tensions:**
[Where the perspectives diverged and why - reveals the tradeoffs]

**The Core Tradeoff:**
[The fundamental choice this decision involves - what are you really choosing between?]

**My Recommendation:**
[Your synthesis considering all three viewpoints - which path forward?]

**Next Step:**
[One concrete action to take in the next 24-48 hours]

---

## Notes

- Cost: ~$0.005 per invocation (3 cheap models)
- Speed: ~3-5 seconds (parallel queries)
- Cognitive diversity: Different AI architectures + different personas',
    NULL
) ON CONFLICT DO NOTHING;
```

### Example 2: Research Council (Deep)

**SQL Insert:**

```sql
INSERT INTO user_skills (
    name,
    description,
    category,
    when_to_use,
    content,
    persona_ids
) VALUES (
    'Research Council',
    'Deep research-backed analysis using vault and calendar context',
    'council',
    'When you need insights grounded in past notes, reflections, and current reality',
    E'# Research Council

Deep analysis using your vault and calendar to ground recommendations in your actual context.

## When to Use

- Planning goals or priorities (need to know what worked/failed before)
- Making decisions about recurring situations (check past similar decisions)
- Strategic planning (need calendar reality + vault wisdom)
- Learning from past experiences (search for patterns)

## Available Subagents

You have access to these subagents via the **Task** tool. Each has specific tools:

- **socratic**: Has vault_search and vault_read. Searches for assumptions and patterns in past notes.
- **contrarian**: Has vault_search and vault_read. Searches for failures and lessons learned.
- **pragmatist**: Has calendar_read and task_list. Checks calendar for constraints and tasks for workload.

## How to Execute

When the user asks to invoke this council:

### Step 1: Invoke Each Subagent

Use the **Task** tool to spawn each subagent with a specific task:

1. **Socratic research:**
   ```
   Task(
       agent_name="socratic",
       task="Search the vault for patterns, assumptions, and past thinking related to: [user''s question]. Look for:
       - Notes with relevant tags
       - Past reflections on similar topics
       - Assumptions that were made before
       - Questions that were asked

       Cite specific notes with dates."
   )
   ```

2. **Contrarian research:**
   ```
   Task(
       agent_name="contrarian",
       task="Search the vault for past failures, lessons learned, and what went wrong related to: [user''s question]. Look for:
       - Retrospective notes
       - Things that didn''t work
       - Overcommitments or underestimations
       - Unexpected disruptions

       Cite specific notes with dates."
   )
   ```

3. **Pragmatist reality check:**
   ```
   Task(
       agent_name="pragmatist",
       task="Check the calendar and task list to understand current reality for: [user''s question]. Look for:
       - Existing commitments
       - Available capacity
       - Upcoming deadlines
       - Current workload

       Provide specific dates and hours."
   )
   ```

### Step 2: Collect Findings

Each subagent will:
- Use their tools (vault_search, calendar_read, etc.)
- Apply their persona''s lens
- Return specific findings with citations
- Provide 2-4 key insights each

Wait for all three to complete.

### Step 3: Synthesize Using This Template

---

## Research Council Analysis

**Question:** [Restate user''s question]

### Research Findings

**Vault Patterns** (Socratic):
[Insert Socratic findings with specific note citations, dates, and quotes]

**Past Lessons** (Contrarian):
[Insert Contrarian findings with retro citations, failure modes, and what to avoid]

**Current Reality** (Pragmatist):
[Insert Pragmatist findings with calendar dates, time blocks, and capacity estimates]

---

### Strategic Synthesis

**Context from Your Past:**
[Summarize what the vault revealed - patterns, questions, assumptions]

**What to Avoid:**
[Based on Contrarian''s findings - failure modes to watch for]

**Realistic Constraints:**
[Based on Pragmatist''s findings - calendar and capacity limits]

**Grounded Recommendation:**
[Your recommendation that accounts for:
- Past patterns (Socratic)
- Past failures (Contrarian)
- Current reality (Pragmatist)]

**Specific Next Action:**
[One concrete step with a date/deadline from the calendar]

**Vault Notes to Review:**
[List 2-3 specific notes the user should re-read based on findings]

---

## Notes

- Cost: ~$0.05-0.08 per invocation (3 Sonnet subagents + tools)
- Speed: ~15-25 seconds (sequential subagent execution + tool calls)
- Depth: Research-backed with vault citations and calendar specifics',
    NULL
) ON CONFLICT DO NOTHING;
```

### Example 3: Creative Council (Fast)

**SQL Insert:**

```sql
INSERT INTO user_skills (
    name,
    description,
    category,
    when_to_use,
    content,
    persona_ids
) VALUES (
    'Creative Council',
    'Rapid ideation and brainstorming using multiple AI models',
    'council',
    'When brainstorming, generating ideas, or facing creative blocks',
    E'# Creative Council

Fast creative brainstorming session with diverse AI perspectives.

## When to Use

- Brainstorming new ideas
- Stuck in creative rut
- Need fresh perspectives on a problem
- Exploring the possibility space
- Breaking out of conventional thinking

## How to Execute

When the user asks to invoke this council:

### Step 1: Query Three Personas

Use **query_persona_with_provider** three times in parallel:

1. **Coach via Claude** (psychological safety, wild ideas):
   ```
   query_persona_with_provider(
       persona_name="Coach",
       provider="anthropic",
       query="Help me brainstorm ideas for: [user''s question]. Encourage wild, unconventional thinking. What would I try if I knew I couldn''t fail?"
   )
   ```

2. **Synthesizer via GPT** (connections, cross-domain):
   ```
   query_persona_with_provider(
       persona_name="Synthesizer",
       provider="openai",
       query="Find unexpected connections and cross-domain inspiration for: [user''s question]. Where else has this been solved? What if we combined X with Y?"
   )
   ```

3. **Contrarian via Gemini** (challenge assumptions):
   ```
   query_persona_with_provider(
       persona_name="Contrarian",
       provider="google",
       query="Challenge conventional thinking about: [user''s question]. What''s the opposite of the obvious solution? What if we changed the constraints?"
   )
   ```

### Step 2: Synthesize Creative Directions

---

## Creative Council Brainstorm

**Challenge:** [Restate user''s creative question]

### Idea Streams

**Encouraging Perspective** (Coach via Claude):
[Insert Coach response - expect psychological safety, permission to think big]

**Cross-Domain Connections** (Synthesizer via GPT):
[Insert Synthesizer response - expect analogies, patterns from other fields]

**Contrarian Provocation** (Contrarian via Gemini):
[Insert Contrarian response - expect assumption challenges, inversions]

---

### Creative Synthesis

**Promising Directions:**
1. [Direction 1 combining insights]
2. [Direction 2 from unexpected connection]
3. [Direction 3 from assumption flip]

**Wild Card Idea:**
[One unconventional option worth considering]

**Recommended First Experiment:**
[Smallest possible test to explore the most promising direction]

**What to Question:**
[Assumptions to examine before proceeding]

---

## Notes

- Cost: ~$0.005 per invocation
- Speed: ~3-5 seconds
- Style: Generative, exploratory, divergent thinking',
    NULL
) ON CONFLICT DO NOTHING;
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_persona_query_tool.py`

```python
import pytest
from core.tools.persona_query import query_persona_with_provider


@pytest.mark.asyncio
async def test_query_persona_with_provider_success(db_session):
    """Test successful persona query."""
    result = await query_persona_with_provider(
        persona_name="Socratic",
        provider="anthropic",
        query="Should I take this job?"
    )

    assert isinstance(result, str)
    assert len(result) > 50
    assert not result.startswith("[Error")


@pytest.mark.asyncio
async def test_query_persona_with_provider_unknown_persona(db_session):
    """Test query with unknown persona."""
    result = await query_persona_with_provider(
        persona_name="NonexistentPersona",
        provider="anthropic",
        query="Test question"
    )

    assert "[Error" in result
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_query_persona_with_provider_unknown_provider(db_session):
    """Test query with unknown provider."""
    result = await query_persona_with_provider(
        persona_name="Socratic",
        provider="unknown_provider",
        query="Test question"
    )

    assert "[Error" in result
    assert "unknown provider" in result.lower()
```

**File:** `tests/test_persona_subagents.py`

```python
import pytest
from core.persona_subagents import create_all_persona_subagents, create_persona_subagent
from claude_agent_sdk import AgentDefinition


@pytest.mark.asyncio
async def test_create_all_persona_subagents(db_session):
    """Test creating subagents for all personas."""
    subagents = await create_all_persona_subagents(db_session)

    # Should have all 5 default personas
    assert len(subagents) >= 5
    assert "socratic" in subagents
    assert "contrarian" in subagents
    assert "pragmatist" in subagents

    # Each should be an AgentDefinition
    for name, agent in subagents.items():
        assert isinstance(agent, AgentDefinition)
        assert agent.name == name
        assert len(agent.prompt) > 100  # Has system prompt


@pytest.mark.asyncio
async def test_create_single_persona_subagent(db_session):
    """Test creating single persona subagent."""
    from core.council import get_persona_by_name

    persona = await get_persona_by_name("Socratic", db_session)
    agent = await create_persona_subagent(persona, db_session)

    assert isinstance(agent, AgentDefinition)
    assert agent.name == "socratic"
    assert "Socratic" in agent.prompt
```

### Integration Tests

**File:** `tests/test_council_integration.py`

```python
import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fast_council_decision(db_session):
    """Test Decision Council (fast mode) end-to-end."""
    from core.tools.persona_query import query_persona_with_provider

    question = "Should I take a new job with 30% raise but unclear scope?"

    # Query all three personas
    socratic_response = await query_persona_with_provider(
        "Socratic", "anthropic", question
    )
    contrarian_response = await query_persona_with_provider(
        "Contrarian", "openai", question
    )
    pragmatist_response = await query_persona_with_provider(
        "Pragmatist", "google", question
    )

    # Verify responses are substantive
    assert len(socratic_response) > 50
    assert len(contrarian_response) > 50
    assert len(pragmatist_response) > 50

    # Verify personas are distinguishable
    assert "?" in socratic_response or "assume" in socratic_response.lower()
    assert "risk" in contrarian_response.lower() or "wrong" in contrarian_response.lower()
    assert "action" in pragmatist_response.lower() or "step" in pragmatist_response.lower()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_deep_council_research(db_session):
    """Test Research Council (deep mode) with Task tool."""
    from claude_agent_sdk import query, ClaudeAgentOptions
    from core.persona_subagents import create_all_persona_subagents

    # Create subagents
    subagents = await create_all_persona_subagents(db_session)

    # Create main agent with subagents
    options = ClaudeAgentOptions(
        model="claude-sonnet-4-5-20250929",
        agents=subagents,
        allowed_tools=["Task", "vault_search", "vault_read"],
        max_tokens=2000,
    )

    # Simulate council invocation
    prompt = """I need to plan my Q1 2026 priorities.

Use the Task tool to:
1. Invoke socratic subagent to search vault for past goal patterns
2. Invoke contrarian subagent to search vault for past failures
3. Then synthesize their findings."""

    full_response = ""
    async for message in query(prompt=prompt, options=options):
        # Collect response (simplified)
        full_response += str(message)

    # Verify subagents were invoked
    assert "socratic" in full_response.lower() or "Task" in full_response
    assert len(full_response) > 200
```

### Manual QA Checklist

- [ ] Start dev server
- [ ] Create chat with default persona
- [ ] Say: "Should I take this job? Invoke Decision Council."
- [ ] Verify: Three tool calls to query_persona_with_provider
- [ ] Verify: Responses from Socratic, Contrarian, Pragmatist
- [ ] Verify: Synthesis follows template format
- [ ] Check: Total time <10 seconds
- [ ] Say: "What should my Q1 priorities be? Invoke Research Council."
- [ ] Verify: Task tool called for subagents
- [ ] Verify: Vault search tool used by subagents
- [ ] Verify: Synthesis includes vault citations
- [ ] Check: Total time <30 seconds

---

## Deployment & Migration

### Phase 1: Tool Implementation (Day 1)

```bash
# 1. Create new file
touch services/brain_runtime/core/tools/persona_query.py

# 2. Implement query_persona_with_provider tool
# (Copy from "Component 1" above)

# 3. Create subagent factory
touch services/brain_runtime/core/persona_subagents.py

# 4. Implement create_all_persona_subagents
# (Copy from "Component 2" above)

# 5. Run tests
cd services/brain_runtime
uv run pytest tests/test_persona_query_tool.py
uv run pytest tests/test_persona_subagents.py
```

### Phase 2: Chat Integration (Day 1)

```bash
# 1. Modify chat endpoint
# Add subagent creation to chat.py
# (See "Component 3" above)

# 2. Test locally
./scripts/dev.sh

# 3. Verify tools available
curl http://localhost:8000/tools | jq '.tools[] | select(.name=="query_persona_with_provider")'
```

### Phase 3: Council Skills (Day 2)

```bash
# 1. Connect to database
psql -d second_brain

# 2. Insert council skills
# Run SQL from "Council Skill Definitions" section

# 3. Verify insertion
SELECT name, category FROM user_skills WHERE category = 'council';

# Expected output:
# Decision Council | council
# Research Council | council
# Creative Council | council
```

### Phase 4: Integration Testing (Day 2)

```bash
# 1. Run integration tests
cd services/brain_runtime
uv run pytest tests/test_council_integration.py -v

# 2. Manual testing
# Open browser to http://localhost:3000
# Create new chat
# Test: "Invoke Decision Council"
# Test: "Invoke Research Council"

# 3. Check logs
tail -f services/brain_runtime/logs/app.log | grep -i council
```

### Phase 5: Production Deploy (Day 3)

```bash
# 1. Ensure API keys configured
# .env should have:
# ANTHROPIC_API_KEY=...
# OPENAI_API_KEY=... (optional for multi-provider)
# GOOGLE_API_KEY=... (optional for multi-provider)

# 2. Run migration (if needed - personas already seeded in 005)
# No new migration needed!

# 3. Deploy backend
git add services/brain_runtime/core/tools/persona_query.py
git add services/brain_runtime/core/persona_subagents.py
git add services/brain_runtime/api/chat.py
git commit -m "feat: Add tool-based council system"
git push

# 4. Deploy frontend (no changes needed!)

# 5. Insert council skills in production DB
psql -d second_brain_production < council_skills.sql
```

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (for multi-provider fast councils)
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...

# Verify setup
python -c "
from core.multi_llm import validate_provider_setup
print(validate_provider_setup())
"
# Output: {'anthropic': True, 'openai': True, 'google': True}
```

---

## Usage Documentation

### For Users

**File:** `docs/user_guide_councils.md`

```markdown
# Using Councils

## What Are Councils?

Councils give you multiple AI perspectives on a question. There are two types:

### Fast Councils (~3-5 seconds)
Get quick perspectives from different AI models (Claude, GPT, Gemini).

**Available:**
- **Decision Council** - For important choices
- **Creative Council** - For brainstorming ideas

**Cost:** ~$0.005 per council (half a penny)

### Deep Councils (~15-25 seconds)
Get research-backed analysis using your vault and calendar.

**Available:**
- **Research Council** - Searches vault for context
- **Strategy Council** - Coming soon

**Cost:** ~$0.05-0.08 per council (5-8 cents)

## How to Invoke

Just mention the council name in your chat:

```
"Should I take this new job? Invoke Decision Council."
```

Or:

```
"What should my Q1 priorities be? Invoke Research Council."
```

The AI will automatically:
1. Load the council instructions
2. Query the personas/subagents
3. Synthesize the results
4. Present formatted analysis

## Example: Decision Council

**You ask:**
> "I got a job offer with 30% raise but unclear scope. Should I take it? Invoke Decision Council."

**You receive:**

### Decision Analysis

**Socratic (via Claude):**
"What assumptions are you making about 'better'? Is this about money, growth, or escaping something?"

**Contrarian (via GPT):**
"Red flag: Unclear scope means they don't know what they want. This could mean constant shifting priorities."

**Pragmatist (via Gemini):**
"First action: Ask for written job description and 30-day plan. If they can't provide it, that's your answer."

**Synthesis:**
All three agree unclear scope is concerning. Recommendation: Don't decide yet. Ask for written scope. If they can't provide it, the Contrarian's warning is validated. If they can, revisit with Socratic's questions.

**Next Step:** Email hiring manager requesting written job description.

## Tips

- Fast councils work best for decisions and brainstorming
- Deep councils work best when you need your own past context
- You can invoke multiple councils for the same question
- Councils complement regular chat - use them when you want structured multi-perspective analysis
```

### For Developers

**File:** `docs/developer_guide_councils.md`

```markdown
# Council System Developer Guide

## Architecture

Councils are **skills containing instructions** that the LLM reads and executes using tools.

### Two Tools

1. **query_persona_with_provider** - Fast councils (LiteLLM)
2. **Task** - Deep councils (SDK subagents)

### No Parsing Required

Council skills are freeform markdown. The LLM:
1. Reads the instructions
2. Calls the appropriate tools
3. Follows the synthesis template

## Creating New Councils

### Fast Council Template

```sql
INSERT INTO user_skills (name, category, when_to_use, content) VALUES (
'[Council Name]',
'council',
'When [trigger condition]',
E'# [Council Name]

[Description]

## How to Execute

Use query_persona_with_provider three times:
1. Query [Persona1] via [provider1]
2. Query [Persona2] via [provider2]
3. Query [Persona3] via [provider3]

## Synthesis Template

[How to combine responses]
'
);
```

### Deep Council Template

```sql
INSERT INTO user_skills (name, category, when_to_use, content) VALUES (
'[Council Name]',
'council',
'When [trigger condition]',
E'# [Council Name]

[Description]

## Available Subagents

- **[subagent1]**: Has [tools]. Does [role].
- **[subagent2]**: Has [tools]. Does [role].

## How to Execute

Use Task tool:
1. Task(agent_name="[subagent1]", task="[specific task]")
2. Task(agent_name="[subagent2]", task="[specific task]")

## Synthesis Template

[How to combine responses]
'
);
```

## Adding New Personas

```sql
-- 1. Create persona
INSERT INTO modes (name, description, icon, color, is_persona, system_prompt_addition)
VALUES ('NewPersona', 'Description', '🎭', '#FF5733', true, 'You are...');

-- 2. Create persona skills
INSERT INTO user_skills (name, description, persona_ids, content)
VALUES ('Persona Skill', 'Description', ARRAY['[persona-id]'], 'Skill content...');

-- 3. Persona automatically available in councils!
-- For fast: reference in council skill
-- For deep: auto-loaded as subagent on next server start
```

## Testing

```python
# Test fast council tool
from core.tools.persona_query import query_persona_with_provider

result = await query_persona_with_provider(
    persona_name="Socratic",
    provider="anthropic",
    query="Test question"
)

# Test deep council subagents
from core.persona_subagents import create_all_persona_subagents

subagents = await create_all_persona_subagents(db)
assert "socratic" in subagents
```

## Debugging

### Check tool registration:
```bash
curl http://localhost:8000/tools | jq '.tools[] | select(.name | contains("persona"))'
```

### Check subagent creation:
```python
# In chat.py, add logging:
logger.info(f"Created {len(subagents)} subagents: {list(subagents.keys())}")
```

### Check council skill injection:
```python
# In skill_loader.py, log when council skills match:
if skill.category == "council":
    logger.info(f"Injecting council skill: {skill.name}")
```

## Performance

- Fast councils: ~3-5s (parallel LiteLLM queries)
- Deep councils: ~15-25s (sequential SDK subagents + tools)
- To optimize: Reduce max_tokens or use Haiku for members

## Cost Tracking

```python
# Add to tool execution:
logger.info(f"Council cost estimate: ${cost:.4f}")

# Monitor in production:
SELECT
    COUNT(*) as invocations,
    SUM(cost_estimate) as total_cost
FROM tool_usage
WHERE tool_name IN ('query_persona_with_provider', 'Task')
    AND created_at > NOW() - INTERVAL '1 day';
```
```

---

## Summary

### What Was Implemented

✅ **query_persona_with_provider tool** (~50 lines)
- Queries personas via LiteLLM
- Supports anthropic, openai, google providers
- Returns persona response as string

✅ **Persona subagent factory** (~30 lines)
- Creates AgentDefinition for all personas
- Makes Task tool available with personas
- Loads persona skills automatically

✅ **Chat integration** (~5 lines)
- Wires subagents into ClaudeAgentOptions
- Makes both tools available
- No parsing needed!

✅ **Council skills** (SQL inserts)
- Decision Council (fast)
- Research Council (deep)
- Creative Council (fast)
- Freeform markdown instructions

### What Was Removed

❌ Parsing logic
❌ Routing logic (fast vs deep)
❌ Custom executors
❌ Mode detection
❌ Special schema columns

### Total Code

- **85 lines** of implementation code
- **3 SQL inserts** for council skills
- **No migrations** needed (personas already exist)

### Time to Production

- Day 1: Tool + subagent implementation
- Day 2: Council skills + testing
- Day 3: Deploy to production

**4 days total vs 3 weeks in parser-based approach**

### Success Metrics

- [ ] Fast councils respond in <5s
- [ ] Deep councils respond in <30s
- [ ] Personas distinguishable in responses
- [ ] Synthesis follows template format
- [ ] Cost tracking accurate
- [ ] No parsing errors (because no parsing!)

**This is the right architecture.** Simple, flexible, fully tool-based. ✅
