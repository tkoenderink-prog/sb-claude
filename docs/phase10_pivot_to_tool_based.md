# Phase 10: Pivot to Tool-Based Architecture

**Date:** 2025-12-23
**Status:** ACTIVE PLAN
**Priority:** CRITICAL - Delete parser-based code, implement tool-based

---

## The Problem

The codebase currently implements a **parser-based council system** that diverges from the approved tool-based architecture. This creates:
- Technical debt
- Architectural inconsistency
- Higher maintenance burden (500+ lines vs 85 lines)
- Higher costs (no prompt caching)
- Less flexibility (rigid structure vs freeform skills)

## The Solution

**Delete all parser-based code and implement the tool-based architecture as documented.**

---

## Rationale: Why Tool-Based Wins

### 1. **Simplicity**
- Parser-based: 500+ lines of parsing, routing, orchestration
- Tool-based: 85 lines total (one tool + subagent factory)

### 2. **Cost**
- Parser-based: $0.055 per council (no caching)
- Tool-based: $0.02 per council (90% savings via prompt caching)

### 3. **Flexibility**
- Parser-based: Rigid `## Members`, `## Protocol` structure
- Tool-based: Freeform markdown instructions, any structure

### 4. **Maintenance**
- Parser-based: We own all orchestration code forever
- Tool-based: Claude Agent SDK handles orchestration

### 5. **Extensibility**
- Parser-based: Add new council = write more parsing code
- Tool-based: Add new council = write markdown instructions

### 6. **Philosophy Alignment**
Skills should be **instructions the LLM reads**, not **data structures code parses**.

---

## Phase 1: Identify and Delete Parser-Based Code

### Files to DELETE Entirely

1. **`services/brain_runtime/core/tools/council_tool.py`**
   - Contains `invoke_council` tool (parser-based)
   - Replaced by: LLM reading skills and calling `query_persona_with_provider` directly

### Functions to DELETE from Existing Files

2. **`services/brain_runtime/core/council.py`**
   - DELETE: `parse_council_skill()` (line 56)
   - DELETE: `execute_council()` (line 127)
   - DELETE: `CouncilDefinition` dataclass
   - DELETE: `MemberConfig` dataclass
   - KEEP: `get_persona_by_name()`, `get_persona_by_id()`
   - ADD: `get_all_personas()`, `get_council_skill_by_name()`

3. **`services/brain_runtime/api/councils.py`**
   - DELETE: `POST /councils/{name}/invoke` endpoint
   - KEEP: `GET /councils` (list councils)
   - KEEP: `GET /councils/{name}` (get council details)

### Database Changes

4. **Council Skills Format**
   - DELETE: All existing council skills (Decision Council with parser format)
   - INSERT: New council skills with tool-based instruction format

---

## Phase 2: Implement Tool-Based Architecture

### Component 1: Query Persona Tool (~50 lines)

**File:** `services/brain_runtime/core/tools/persona_query.py` (NEW)

**Purpose:** Query any persona using any LLM provider (anthropic, openai, google)

**Dependencies:**
- `litellm` package (`pip install litellm` or add to pyproject.toml)
- `core.council.get_persona_by_name`
- `core.skill_loader.load_skills_for_persona`
- `core.skill_loader.build_persona_system_prompt`

**Key Features:**
- Takes `persona_name`, `provider`, `query` as params
- Loads persona from database
- Loads persona's exclusive skills
- Builds complete system prompt
- Calls LiteLLM with provider-specific model
- Returns persona's response

### Component 2: Persona Subagents Factory (~30 lines)

**File:** `services/brain_runtime/core/persona_subagents.py` (NEW)

**Purpose:** Create AgentDefinition objects for all personas (for deep councils)

**Dependencies:**
- `claude_agent_sdk.AgentDefinition`
- `core.council.get_all_personas` (need to add this function)
- `core.skill_loader` functions

**Key Features:**
- Iterates through all personas in database
- For each persona:
  - Loads exclusive skills
  - Builds system prompt
  - Creates AgentDefinition with subagent instructions
  - Adds to dict keyed by persona name (lowercase)
- Returns dict for use in ClaudeAgentOptions

### Component 3: Chat Integration (~10 lines)

**File:** `services/brain_runtime/api/chat.py` (MODIFY)

**Changes:**
- Import `create_all_persona_subagents`
- In chat endpoint, before creating options:
  - `subagents = await create_all_persona_subagents(db)`
- Add to ClaudeAgentOptions:
  - `agents=subagents`
  - `allowed_tools=["Task", "query_persona_with_provider", ...]`

### Component 4: Tool Registration

**File:** `services/brain_runtime/core/tools/registry.py` (VERIFY)

**Ensure:** The `@tool` decorator on `query_persona_with_provider` auto-registers it

### Component 5: Helper Functions

**File:** `services/brain_runtime/core/council.py` (ADD)

**New Functions:**
```python
async def get_all_personas(db: AsyncSession) -> List[ModeDB]:
    """Get all personas from database."""
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

### Component 6: LiteLLM Configuration

**File:** `services/brain_runtime/core/multi_llm.py` (NEW or extend existing)

**Purpose:** Provider model mapping

```python
PROVIDER_MODELS = {
    "anthropic": "claude-haiku-4-5-20251001",
    "openai": "gpt-4o-mini",
    "google": "gemini/gemini-2.0-flash-exp",
}

def get_available_providers() -> list[str]:
    """Get providers with valid API keys."""
    available = []
    for provider, config in PROVIDER_CONFIGS.items():
        if os.getenv(config["env_key"]):
            available.append(provider)
    return available
```

---

## Phase 3: Rewrite Council Skills (Tool-Based Format)

### Delete Old Council Skills

```sql
-- Remove parser-based Decision Council
DELETE FROM user_skills WHERE name = 'Decision Council' AND category = 'council';
```

### Insert Tool-Based Council Skills

**1. Decision Council (Fast)**

```sql
INSERT INTO user_skills (
    name, description, category, when_to_use, content
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

## How to Execute

When the user asks to invoke this council:

### Step 1: Query Three Personas

Use the **query_persona_with_provider** tool three times (you can call them in parallel):

1. Socratic perspective via Claude:
   query_persona_with_provider(persona_name="Socratic", provider="anthropic", query="[user question]")

2. Contrarian perspective via GPT:
   query_persona_with_provider(persona_name="Contrarian", provider="openai", query="[user question]")

3. Pragmatist perspective via Gemini:
   query_persona_with_provider(persona_name="Pragmatist", provider="google", query="[user question]")

### Step 2: Synthesize

Present all three responses using this template:

---

## Decision Analysis

**Question:** [Restate user decision]

### Perspectives

**Socratic (via Claude Haiku):**
[Insert response - expect questions and assumption probing]

**Contrarian (via GPT-4o-mini):**
[Insert response - expect risk analysis and failure modes]

**Pragmatist (via Gemini Flash):**
[Insert response - expect action items and next steps]

---

### My Synthesis

**Consensus:** [What all three agreed on]

**Key Tensions:** [Where perspectives diverged and why]

**The Core Tradeoff:** [The fundamental choice]

**My Recommendation:** [Your synthesis considering all viewpoints]

**Next Step:** [One concrete action within 24-48 hours]

---

## Notes
- Cost: ~$0.005 per invocation
- Speed: ~3-5 seconds (parallel queries)
'
) ON CONFLICT DO NOTHING;
```

**2. Research Council (Deep)**

```sql
INSERT INTO user_skills (
    name, description, category, when_to_use, content
) VALUES (
    'Research Council',
    'Deep research-backed analysis using vault and calendar context',
    'council',
    'When you need insights grounded in past notes, reflections, and current reality',
    E'# Research Council

Deep analysis using vault and calendar to ground recommendations in actual context.

## When to Use
- Planning goals or priorities
- Making decisions about recurring situations
- Strategic planning with calendar reality check

## Available Subagents

You have access to these subagents via the **Task** tool:

- **socratic**: Has vault_search and vault_read. Searches for assumptions and patterns in past notes.
- **contrarian**: Has vault_search and vault_read. Searches for failures and lessons learned.
- **pragmatist**: Has calendar_read and task_list. Checks calendar for constraints and workload.

## How to Execute

When the user asks to invoke this council:

### Step 1: Invoke Each Subagent

Use the **Task** tool to spawn each subagent:

Task(agent_name="socratic", task="Search the vault for patterns, assumptions, and past thinking related to: [user question]. Look for notes with relevant tags, past reflections, and questions asked before. Cite specific notes with dates.")

Task(agent_name="contrarian", task="Search the vault for past failures, lessons learned, and what went wrong related to: [user question]. Look for retrospectives, things that didn''t work, and unexpected disruptions. Cite specific notes.")

Task(agent_name="pragmatist", task="Check calendar and task list to understand current reality for: [user question]. Look for existing commitments, available capacity, upcoming deadlines. Provide specific dates and hours.")

### Step 2: Synthesize

---

## Research Council Analysis

**Question:** [Restate user question]

### Research Findings

**Vault Patterns** (Socratic):
[Insert findings with note citations and dates]

**Past Lessons** (Contrarian):
[Insert findings with failure citations]

**Current Reality** (Pragmatist):
[Insert findings with calendar dates and capacity]

---

### Strategic Synthesis

**Context from Your Past:** [Summarize vault insights]

**What to Avoid:** [Based on past failures]

**Realistic Constraints:** [Based on calendar/capacity]

**Grounded Recommendation:** [Accounts for patterns, failures, and reality]

**Specific Next Action:** [One step with a date from calendar]

**Vault Notes to Review:** [2-3 specific notes to re-read]

---

## Notes
- Cost: ~$0.05-0.08 per invocation
- Speed: ~15-25 seconds
'
) ON CONFLICT DO NOTHING;
```

**3. Creative Council (Fast)**

```sql
INSERT INTO user_skills (
    name, description, category, when_to_use, content
) VALUES (
    'Creative Council',
    'Rapid ideation and brainstorming using multiple AI models',
    'council',
    'When brainstorming, generating ideas, or facing creative blocks',
    E'# Creative Council

Fast creative brainstorming with diverse AI perspectives.

## When to Use
- Brainstorming new ideas
- Stuck in creative rut
- Need fresh perspectives
- Breaking conventional thinking

## How to Execute

When the user asks to invoke this council:

### Step 1: Query Three Personas

Use **query_persona_with_provider** three times in parallel:

query_persona_with_provider(persona_name="Coach", provider="anthropic", query="Help me brainstorm ideas for: [user question]. Encourage wild, unconventional thinking. What would I try if I knew I couldn''t fail?")

query_persona_with_provider(persona_name="Synthesizer", provider="openai", query="Find unexpected connections and cross-domain inspiration for: [user question]. Where else has this been solved? What if we combined X with Y?")

query_persona_with_provider(persona_name="Contrarian", provider="google", query="Challenge conventional thinking about: [user question]. What''s the opposite of the obvious solution? What if we changed the constraints?")

### Step 2: Synthesize

---

## Creative Council Brainstorm

**Challenge:** [Restate user question]

### Idea Streams

**Encouraging Perspective** (Coach via Claude):
[Insert response - psychological safety, permission to think big]

**Cross-Domain Connections** (Synthesizer via GPT):
[Insert response - analogies, patterns from other fields]

**Contrarian Provocation** (Contrarian via Gemini):
[Insert response - assumption challenges, inversions]

---

### Creative Synthesis

**Promising Directions:**
1. [Direction 1 combining insights]
2. [Direction 2 from unexpected connection]
3. [Direction 3 from assumption flip]

**Wild Card Idea:** [One unconventional option worth considering]

**Recommended First Experiment:** [Smallest test of most promising direction]

**What to Question:** [Assumptions to examine before proceeding]

---

## Notes
- Cost: ~$0.005 per invocation
- Speed: ~3-5 seconds
'
) ON CONFLICT DO NOTHING;
```

---

## Phase 4: Testing Strategy

### Unit Tests

**File:** `services/brain_runtime/tests/test_persona_query_tool.py` (NEW)

```python
import pytest
from core.tools.persona_query import query_persona_with_provider

@pytest.mark.asyncio
async def test_query_persona_success(db_session):
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
async def test_query_persona_unknown_persona(db_session):
    """Test query with unknown persona."""
    result = await query_persona_with_provider(
        persona_name="NonexistentPersona",
        provider="anthropic",
        query="Test"
    )
    assert "[Error" in result
    assert "not found" in result.lower()
```

**File:** `services/brain_runtime/tests/test_persona_subagents.py` (NEW)

```python
import pytest
from core.persona_subagents import create_all_persona_subagents
from claude_agent_sdk import AgentDefinition

@pytest.mark.asyncio
async def test_create_all_subagents(db_session):
    """Test creating all persona subagents."""
    subagents = await create_all_persona_subagents(db_session)

    assert len(subagents) >= 5
    assert "socratic" in subagents
    assert "contrarian" in subagents

    for name, agent in subagents.items():
        assert isinstance(agent, AgentDefinition)
        assert agent.name == name
        assert len(agent.prompt) > 100
```

### Integration Tests

**File:** `services/brain_runtime/tests/test_council_integration.py` (NEW)

Test full council flow with real LLM calls (mark as slow/integration).

### Manual Testing

1. Start servers: `./scripts/dev.sh`
2. Create chat with Socratic as lead
3. Ask: "Should I quit my job to travel? Invoke Decision Council."
4. Verify:
   - Three tool calls to `query_persona_with_provider`
   - Responses from different providers
   - Synthesis follows template

---

## Phase 5: Deployment Plan

### Day 1: Core Implementation

**Morning (4 hours):**
1. Delete parser-based code
2. Implement `persona_query.py` (~50 lines)
3. Implement `persona_subagents.py` (~30 lines)
4. Add helper functions to `council.py`

**Afternoon (4 hours):**
5. Update chat integration
6. Add LiteLLM config
7. Run unit tests
8. Fix any import errors

### Day 2: Council Skills & Testing

**Morning (4 hours):**
1. Delete old council skills from database
2. Insert 3 new tool-based council skills
3. Verify skills load correctly
4. Test skill injection works

**Afternoon (4 hours):**
5. Manual testing (invoke each council)
6. Integration tests
7. Fix any issues found
8. Update documentation

### Day 3: Polish & Deploy

**Morning (3 hours):**
1. Fix remaining lint errors
2. Update CLAUDE.md
3. Commit with clear message
4. Create migration script if needed

**Afternoon (2 hours):**
5. Deploy to production
6. Smoke test all three councils
7. Monitor logs for errors
8. Document any issues

---

## Dependencies

### Python Packages

Add to `pyproject.toml`:
```toml
[project]
dependencies = [
    # ... existing deps ...
    "litellm>=1.0.0",  # For multi-provider support
]
```

Install:
```bash
cd services/brain_runtime
uv add litellm
```

### Environment Variables

Required in `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-...  # Required
OPENAI_API_KEY=sk-proj-...     # Optional (for multi-provider)
GOOGLE_API_KEY=...             # Optional (for multi-provider)
```

---

## Validation Checklist

Before marking complete:

- [ ] All parser-based code deleted
- [ ] `query_persona_with_provider` tool implemented and registered
- [ ] `create_all_persona_subagents` factory implemented
- [ ] Chat integration includes subagents
- [ ] Helper functions added (`get_all_personas`, `get_council_skill_by_name`)
- [ ] LiteLLM configured with provider models
- [ ] Old council skills deleted from database
- [ ] 3 new tool-based council skills inserted
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing: Decision Council works
- [ ] Manual testing: Research Council works
- [ ] Manual testing: Creative Council works
- [ ] CLAUDE.md updated with tool-based architecture
- [ ] Lint errors fixed
- [ ] Deployed to production

---

## Success Metrics

**Code Simplicity:**
- Parser-based: ~500 lines deleted
- Tool-based: ~85 lines added
- Net reduction: ~415 lines (83% less code)

**Cost:**
- Before: $0.055 per council
- After: $0.02 per council
- Savings: 64% reduction

**Flexibility:**
- Before: Rigid structure, custom parsing
- After: Freeform markdown, LLM reads directly

**Maintenance:**
- Before: We maintain orchestration code
- After: Claude Agent SDK handles it

---

## Risk Mitigation

**Risk:** LiteLLM integration fails
**Mitigation:** Start with Anthropic only, add OpenAI/Google later

**Risk:** Prompt caching doesn't work as expected
**Mitigation:** Test with extended-cache-ttl beta header, monitor costs

**Risk:** Subagents don't have tool access
**Mitigation:** Verify AgentDefinition setup in tests first

**Risk:** Skills don't inject correctly
**Mitigation:** Test skill injection system before rewriting all councils

---

## Post-Pivot Cleanup

Once tool-based is working:

1. Remove unused imports from deleted files
2. Run `uv run ruff check . --fix` to clean up
3. Update any stale comments referencing parser-based approach
4. Archive parser-based docs if any exist
5. Update developer guide with tool-based examples

---

**END OF PIVOT PLAN**

This plan will be executed immediately. No more parser-based code after this.
