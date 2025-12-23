# Phase 10: Tool-Based Councils - Executive Summary

**Date:** 2025-12-22
**Status:** NEW ARCHITECTURE - Tool-Based (No Parsing!)
**Supersedes:** Previous parser-based approach

---

## The Evolution of Thinking

### Original Approach (Parser-Based)
```
User invokes council
    ↓
Custom parser extracts mode/members from markdown
    ↓
If mode=fast → execute_fast_council()
If mode=deep → execute_deep_council()
    ↓
Custom code orchestrates LLM calls
    ↓
Return result
```

**Problems:**
- ❌ Custom parsing logic for markdown
- ❌ Custom routing logic (fast vs deep)
- ❌ Council skills are "data" that gets parsed
- ❌ Overengineered (required_tools column, mode detection, etc.)

### New Approach (Tool-Based)
```
User invokes council
    ↓
LLM reads council skill (it's just instructions)
    ↓
LLM uses tools to execute (query_persona or Task)
    ↓
LLM follows synthesis template from skill
    ↓
Return result
```

**Benefits:**
- ✅ No parsing needed - LLM reads instructions
- ✅ No routing needed - skill says which tools to use
- ✅ Council skills are **programs written in natural language**
- ✅ Fully aligned with skills philosophy
- ✅ Simple, elegant, composable

---

## Core Insight: Skills Are Instructions, Not Data

**Previous mental model:**
> Council skills are **data structures** that get parsed and executed by custom code

**New mental model:**
> Council skills are **natural language programs** that the LLM reads and executes using tools

**Example:**

**As data (parser-based):**
```markdown
**Mode:** fast
**Providers:** anthropic,openai,google
**Members:** Socratic, Contrarian, Pragmatist
```
↓ Parser extracts these fields
↓ Custom code executes

**As instructions (tool-based):**
```markdown
When invoked, use the query_persona_with_provider tool three times:
1. Query Socratic using Anthropic
2. Query Contrarian using OpenAI
3. Query Pragmatist using Google

Then synthesize the responses.
```
↓ LLM reads this
↓ LLM uses tools
↓ LLM synthesizes

**The second is simpler and more powerful!**

---

## Architecture: Two Execution Paths

### Path 1: Fast Councils (Multi-Provider via LiteLLM)

**New Tool:**
```python
@tool(name="query_persona_with_provider")
async def query_persona_with_provider(
    persona_name: str,
    provider: str,  # "anthropic", "openai", "google"
    query: str
) -> str:
    """Query a specific persona using a specific LLM provider.

    This enables getting perspectives from different AI architectures
    (Claude's reasoning, GPT's knowledge, Gemini's speed).
    """
    # 1. Load persona definition
    persona = await get_persona_by_name(persona_name, db)

    # 2. Load persona's exclusive skills
    skills = await load_skills_for_persona(persona.id, db)

    # 3. Build complete system prompt
    system_prompt = build_persona_system_prompt(
        base_prompt="",
        persona=persona,
        skills=skills
    )

    # 4. Map provider to model
    model = PROVIDER_MODELS[provider]  # e.g., "anthropic" → "claude-haiku-4-5"

    # 5. Call LiteLLM
    response = await litellm.acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        max_tokens=300,
        temperature=0.7
    )

    return response.choices[0].message.content
```

**Council Skill (Instructions):**
```markdown
# Decision Council

Quick multi-perspective analysis from different AI providers.

## When to Use
Important decisions, strategic choices, situations with multiple valid options.

## How to Execute

When the user asks to invoke this council:

1. **Query three personas using different providers:**
   - Use query_persona_with_provider(persona_name="Socratic", provider="anthropic", query=user_question)
   - Use query_persona_with_provider(persona_name="Contrarian", provider="openai", query=user_question)
   - Use query_persona_with_provider(persona_name="Pragmatist", provider="google", query=user_question)

   You can call these in parallel for speed.

2. **You will receive three responses:**
   - Socratic (via Claude): Questions assumptions
   - Contrarian (via GPT): Identifies risks
   - Pragmatist (via Gemini): Suggests actions

3. **Synthesize using this template:**

   ## Decision Analysis

   **Socratic Perspective** (via Claude Haiku):
   [Insert Socratic response]

   **Contrarian Perspective** (via GPT-4o-mini):
   [Insert Contrarian response]

   **Pragmatist Perspective** (via Gemini Flash):
   [Insert Pragmatist response]

   ---

   **My Synthesis:**

   **Consensus:** [What all three agreed on]

   **Key Tensions:** [Where perspectives diverged and why]

   **The Core Tradeoff:** [The fundamental choice this decision involves]

   **My Recommendation:** [Your synthesis, considering all three viewpoints]

   **Next Step:** [One concrete action to take]

## Cost & Speed
- ~$0.006 per invocation
- ~3-5 seconds total
```

**How It Works:**
1. User: "Should I take the new job? Invoke Decision Council."
2. LLM sees user mentioned "Decision Council"
3. LLM loads Decision Council skill (via skill injection)
4. LLM reads instructions: "Use query_persona_with_provider three times..."
5. LLM calls tool three times with different providers
6. LLM receives three responses
7. LLM follows synthesis template from skill
8. LLM returns formatted decision analysis

**No parsing. No routing. Just following instructions!**

---

### Path 2: Deep Councils (SDK Subagents with Tools)

**Existing Tool:** `Task` (built into Claude Agent SDK)

**Setup:** Define personas as AgentDefinition objects

```python
# At startup, create subagent definitions for all personas
subagents = {}
for persona in get_all_personas():
    skills = load_skills_for_persona(persona.id)
    system_prompt = build_persona_system_prompt(persona, skills)

    subagents[persona.name.lower()] = AgentDefinition(
        name=persona.name.lower(),
        description=persona.description,
        prompt=system_prompt,
        model="claude-sonnet-4-5-20250929"
    )

# Make these available to main agent
options = ClaudeAgentOptions(
    agents=subagents,  # socratic, contrarian, pragmatist, etc.
    allowed_tools=["Task", "vault_search", "calendar_read", "task_list"]
)
```

**Council Skill (Instructions):**
```markdown
# Research Council

Deep research-backed analysis using vault context.

## When to Use
When you need insights grounded in past notes, reflections, and historical patterns.

## Available Subagents

You have access to these subagents via the Task tool:

- **socratic**: Searches vault for assumptions and patterns. Has vault_search and vault_read.
- **contrarian**: Searches vault for failures and lessons. Has vault_search and vault_read.
- **pragmatist**: Checks calendar and tasks for realistic constraints. Has calendar_read and task_list.

## How to Execute

When the user asks to invoke this council:

1. **Invoke each subagent using the Task tool:**

   Task(agent_name="socratic", task="Search the vault for patterns related to: [user's question]. Look for past assumptions, recurring themes, and what I've learned before about this topic.")

   Task(agent_name="contrarian", task="Search the vault for past failures or lessons learned related to: [user's question]. What went wrong before? What should I avoid?")

   Task(agent_name="pragmatist", task="Check my calendar and task list to assess realistic capacity for: [user's question]. What constraints exist?")

2. **Each subagent will:**
   - Use their tools (vault_search, calendar_read, etc.)
   - Apply their persona's reasoning style
   - Return findings with specific citations

3. **Synthesize using this template:**

   ## Research Council Analysis

   **Vault Insights** (Socratic):
   [Insert Socratic findings with note citations]

   **Past Lessons** (Contrarian):
   [Insert Contrarian findings with failure citations]

   **Current Reality** (Pragmatist):
   [Insert Pragmatist findings with calendar constraints]

   ---

   **Strategic Synthesis:**

   **Context from Your Past Thinking:**
   [Summarize vault insights]

   **What to Avoid:**
   [Based on past failures]

   **Realistic Path Forward:**
   [Based on calendar reality]

   **Recommended Action:**
   [Specific next step grounded in all three sources]

## Cost & Speed
- ~$0.05-0.08 per invocation
- ~15-25 seconds total
```

**How It Works:**
1. User: "What should my Q1 priorities be? Invoke Research Council."
2. LLM sees "Research Council" mentioned
3. LLM loads Research Council skill
4. LLM reads instructions: "Invoke each subagent using Task tool..."
5. LLM uses Task tool three times (sequentially or in sequence)
6. Each subagent uses their tools (vault_search, calendar_read)
7. Each subagent returns findings
8. LLM follows synthesis template from skill
9. LLM returns research-backed analysis

**No parsing. No custom orchestration. Just LLM reading instructions and using tools!**

---

## Mode Selection: Implicit in Tool Choice

**Question:** How does the system know whether to use fast (LiteLLM) or deep (SDK) mode?

**Answer:** It doesn't need to know! The skill content determines it:

**Fast council skill mentions:**
- "query_persona_with_provider tool"
- "different AI providers"
- "Claude, GPT, Gemini"

**Deep council skill mentions:**
- "Task tool"
- "subagents"
- "vault_search, calendar_read"

**The LLM reads the instructions and uses the appropriate tool naturally.**

No `**Mode:** fast` declaration needed. The tool names in the instructions are self-documenting.

---

## What Gets Simplified

### Before (Parser-Based)

**Schema:**
- ❌ `required_tools` column on user_skills
- ❌ Custom council parsing logic
- ❌ Mode detection regex
- ❌ Member extraction regex

**Code:**
- ❌ `parse_council_skill()` function
- ❌ `execute_fast_council()` custom executor
- ❌ `execute_deep_council()` custom executor
- ❌ Router that dispatches based on mode

**Council skill format:**
- ❌ Rigid markdown structure
- ❌ Special `**Mode:**` declaration
- ❌ Special `**Providers:**` declaration
- ❌ Special `**Tools:**` declaration

### After (Tool-Based)

**Schema:**
- ✅ No changes! Use existing user_skills table

**Code:**
- ✅ One tool: `query_persona_with_provider` (~30 lines)
- ✅ Startup: Create AgentDefinition objects for personas
- ✅ That's it!

**Council skill format:**
- ✅ Freeform markdown (any structure)
- ✅ Natural language instructions
- ✅ Examples of tool usage
- ✅ Synthesis template (any format)

---

## Complete Data Model

### 1. Personas (Already Complete ✅)

```sql
-- From migration 005
SELECT name, description, icon, system_prompt_addition
FROM modes
WHERE is_persona = true;

/*
Socratic    | Questions assumptions | 🏛️ | "You are a Socratic questioner..."
Contrarian  | Finds weaknesses      | 😈 | "You are a devil's advocate..."
Pragmatist  | Drives to action      | 🎯 | "You are a pragmatist..."
Synthesizer | Finds patterns        | 🔮 | "You are a systems thinker..."
Coach       | Supportive growth     | 🌱 | "You are a supportive coach..."
*/
```

### 2. Persona Skills (Already Complete ✅)

```sql
-- From migration 005
SELECT name, description, persona_ids
FROM user_skills
WHERE persona_ids IS NOT NULL;

/*
Examples:
- "Socratic Questioning" → persona_ids: [socratic-uuid]
- "Premortem Analysis" → persona_ids: [contrarian-uuid]
- "80/20 Analysis" → persona_ids: [pragmatist-uuid]
*/
```

### 3. Council Skills (New Format)

```sql
INSERT INTO user_skills (
    name,
    description,
    category,
    when_to_use,
    content
) VALUES (
    'Decision Council',
    'Multi-perspective analysis from different AI providers',
    'council',
    'When facing important decisions',
    E'# Decision Council

[Full instructions as shown above - freeform markdown]
- Tells LLM to use query_persona_with_provider
- Provides synthesis template
- No special fields to parse!'
);
```

**Key difference:** Content is **instructions**, not **data structure**.

---

## Tools Needed

### Tool 1: query_persona_with_provider (Fast Councils)

**Purpose:** Query any persona using any LLM provider

**Implementation:**
```python
# core/tools/persona_query.py

from litellm import acompletion
from core.skill_loader import load_skills_for_persona, build_persona_system_prompt
from core.council import get_persona_by_name

@tool(
    name="query_persona_with_provider",
    description="""Query a specific persona using a specific LLM provider.

Use this to get perspectives from different AI architectures:
- anthropic: Claude (nuanced reasoning)
- openai: GPT (broad knowledge)
- google: Gemini (fast, efficient)

Example:
query_persona_with_provider(
    persona_name="Socratic",
    provider="anthropic",
    query="Should I take this job offer?"
)""",
    parameters={
        "type": "object",
        "properties": {
            "persona_name": {
                "type": "string",
                "description": "Name of persona (Socratic, Contrarian, Pragmatist, etc.)"
            },
            "provider": {
                "type": "string",
                "enum": ["anthropic", "openai", "google"],
                "description": "LLM provider to use"
            },
            "query": {
                "type": "string",
                "description": "The question or task to present to the persona"
            }
        },
        "required": ["persona_name", "provider", "query"]
    }
)
async def query_persona_with_provider(
    persona_name: str,
    provider: str,
    query: str
):
    """Query a persona using a specific LLM provider."""
    from core.database import get_session_factory

    async with get_session_factory()() as db:
        # Load persona
        persona = await get_persona_by_name(persona_name, db)
        if not persona:
            return f"Error: Persona '{persona_name}' not found"

        # Load persona's skills
        skills = await load_skills_for_persona(str(persona.id), db)

        # Build system prompt
        system_prompt = build_persona_system_prompt(
            base_prompt="",
            persona=persona,
            skills=skills
        )

        # Map provider to model
        PROVIDER_MODELS = {
            "anthropic": "claude-haiku-4-5-20251001",
            "openai": "gpt-4o-mini",
            "google": "gemini/gemini-2.0-flash-exp"
        }

        model = PROVIDER_MODELS.get(provider)
        if not model:
            return f"Error: Unknown provider '{provider}'"

        # Query via LiteLLM
        try:
            response = await acompletion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=300,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error querying {provider}: {str(e)}"
```

**That's it! ~50 lines.**

### Tool 2: Task (Deep Councils)

**Already exists in Claude Agent SDK!**

Just need to define personas as AgentDefinition objects:

```python
# core/persona_subagents.py

from claude_agent_sdk import AgentDefinition
from core.skill_loader import load_skills_for_persona, build_persona_system_prompt

async def create_all_persona_subagents(db) -> dict:
    """Create AgentDefinition objects for all personas.

    These become available to the main agent via the Task tool.
    """
    from core.council import get_all_personas

    subagents = {}

    personas = await get_all_personas(db)

    for persona in personas:
        # Load persona's skills
        skills = await load_skills_for_persona(str(persona.id), db)

        # Build system prompt
        system_prompt = build_persona_system_prompt(
            base_prompt="",
            persona=persona,
            skills=skills
        )

        # Create subagent
        subagents[persona.name.lower()] = AgentDefinition(
            name=persona.name.lower(),
            description=f"{persona.name}: {persona.description}",
            prompt=system_prompt,
            model="claude-sonnet-4-5-20250929"
        )

    return subagents
```

**Usage in main chat:**
```python
# When starting chat session
subagents = await create_all_persona_subagents(db)

options = ClaudeAgentOptions(
    model="claude-sonnet-4-5-20250929",
    agents=subagents,  # Makes Task tool available with all personas
    allowed_tools=["Task", "vault_search", "calendar_read", "task_list", "query_persona_with_provider"]
)
```

---

## Skill Injection Flow

**How does the LLM get the council skill when user mentions it?**

### Option A: Existing Skill Injection System

**Already implemented in Phase 7-9!**

```python
# From existing codebase
def build_system_prompt_with_skills(
    mode: str,
    messages: List[dict],
    session_id: str,
    attached_skills: List[str],
    already_injected: List[str],
) -> tuple[str, List[str]]:
    """Inject skills based on conversation content."""

    # Existing logic already handles:
    # 1. Keyword matching in messages
    # 2. when_to_use matching
    # 3. Skill content injection

    # Council skills work the same way!
    # If user says "Invoke Decision Council"
    # → Skill injection sees "Decision Council" in message
    # → Loads skill with name="Decision Council"
    # → Injects content into system prompt
    # → LLM reads instructions and uses tools
```

**No changes needed!** Council skills auto-inject just like other skills.

### Option B: Explicit Load (Alternative)

```python
# If user explicitly says "Invoke Decision Council"
# Could add a tool:

@tool(name="load_council_skill")
async def load_council_skill(council_name: str):
    """Load the instructions for a specific council."""
    skill = await get_skill_by_name(council_name)
    return skill.content  # Returns the markdown instructions
```

But Option A (existing injection) is cleaner!

---

## Example: Complete User Flow

**User asks:**
```
"I got a job offer with 30% raise but unclear scope.
Should I take it? Invoke Decision Council."
```

**System flow:**

1. **Skill injection (existing system):**
   - Sees "Decision Council" in user message
   - Loads skill: `SELECT * FROM user_skills WHERE name = 'Decision Council'`
   - Injects skill.content into system prompt

2. **LLM reads skill content:**
   ```
   # Decision Council

   When the user asks to invoke this council:

   1. Use query_persona_with_provider three times:
      - query_persona_with_provider(persona_name="Socratic", provider="anthropic", query=user_question)
      ...
   ```

3. **LLM follows instructions:**
   - Calls query_persona_with_provider("Socratic", "anthropic", "Should I take it?")
   - Calls query_persona_with_provider("Contrarian", "openai", "Should I take it?")
   - Calls query_persona_with_provider("Pragmatist", "google", "Should I take it?")

4. **Tool executes:**
   - Each call loads the persona (Socratic, Contrarian, Pragmatist)
   - Each call loads persona's exclusive skills
   - Each call builds persona's system prompt
   - Each call queries the specified provider (Claude, GPT, Gemini)
   - Each call returns the response

5. **LLM receives three responses:**
   - Socratic (via Claude): "What assumptions are you making about 'better'?"
   - Contrarian (via GPT): "Here's what could go wrong: unclear scope is a red flag..."
   - Pragmatist (via Gemini): "First step: ask for written scope. Second: ..."

6. **LLM follows synthesis template from skill:**
   ```
   ## Decision Analysis

   **Socratic Perspective** (via Claude Haiku):
   What assumptions are you making about "better"?...

   **Contrarian Perspective** (via GPT-4o-mini):
   Here's what could go wrong...

   **Pragmatist Perspective** (via Gemini Flash):
   First step: ask for written scope...

   ---

   **My Synthesis:**

   **Consensus:** All three agree unclear scope is concerning.

   **Key Tensions:** Socratic wants you to clarify values first,
   Contrarian says walk away if scope stays unclear, Pragmatist
   says gather data before deciding.

   **The Core Tradeoff:** Money vs clarity and control

   **My Recommendation:** Don't decide yet. The Pragmatist is right:
   ask for written job description and 30-day plan. If they can't
   provide it, that's your answer (Contrarian's warning validated).
   If they can, then revisit with Socratic's questions about what
   "better" means to you.

   **Next Step:** Email hiring manager: "Before I can decide, I need
   a written job description and clarity on the first 30 days."
   ```

**Total time:** ~4 seconds
**Total cost:** ~$0.006
**No parsing. No routing. Just LLM reading and following instructions.**

---

## Implementation Complexity

### Code Required

**1. One tool (~50 lines):**
```python
# core/tools/persona_query.py
@tool(name="query_persona_with_provider")
async def query_persona_with_provider(persona_name, provider, query):
    # Load persona + skills
    # Build system prompt
    # Call LiteLLM
    # Return response
```

**2. Subagent factory (~30 lines):**
```python
# core/persona_subagents.py
async def create_all_persona_subagents(db):
    # For each persona:
    #   Load skills
    #   Build system prompt
    #   Create AgentDefinition
    # Return dict of subagents
```

**3. Wire up in chat (~5 lines):**
```python
# In chat endpoint
subagents = await create_all_persona_subagents(db)
options = ClaudeAgentOptions(
    agents=subagents,
    allowed_tools=["Task", "query_persona_with_provider", ...]
)
```

**Total: ~85 lines of code**

### No Code Required For

- ❌ Parsing council skills
- ❌ Extracting mode/members/providers
- ❌ Routing logic (fast vs deep)
- ❌ Custom council executors
- ❌ Synthesis logic

**The LLM does all of this by reading the skill!**

---

## What You Can Define (Pure Data)

### 1. Personas ✅
Already complete from migration 005.

### 2. Persona Skills ✅
Already complete from migration 005.

### 3. Council Skills (New Format)

**Just insert markdown instructions:**

```sql
INSERT INTO user_skills (name, category, when_to_use, content) VALUES
('Decision Council', 'council', 'Important decisions', '[Instructions...]'),
('Research Council', 'council', 'Need vault context', '[Instructions...]'),
('Strategy Council', 'council', 'Long-term planning', '[Instructions...]');
```

**The instructions can be:**
- Any markdown structure
- Any tool usage pattern
- Any synthesis template
- Completely freeform!

---

## Benefits of Tool-Based Approach

### 1. Simplicity
- No parsing logic
- No routing logic
- No custom executors
- Just tools + instructions

### 2. Flexibility
- Council skills can have any structure
- Can mix fast + deep in one council
- Can call tools in any order
- LLM decides based on instructions

### 3. Composability
- Personas defined once, used everywhere
- Skills defined once per persona
- Councils reference them by name
- Everything pure data

### 4. Debuggability
- Tool calls visible in trace
- Can see exactly what LLM did
- Instructions are readable natural language
- No opaque parsing/routing

### 5. Extensibility
- Add new personas → immediately available to councils
- Add new tools → councils can use them
- Add new providers → query_persona_with_provider supports them
- No code changes

---

## Migration Path

### Phase 1: Add query_persona_with_provider Tool
- Implement tool (~50 lines)
- Register in tool registry
- Test with one persona + one provider

### Phase 2: Create Persona Subagents
- Implement factory (~30 lines)
- Wire up in chat endpoint
- Test Task tool with personas

### Phase 3: Create Council Skills
- Write Decision Council skill (fast mode)
- Write Research Council skill (deep mode)
- Insert via SQL

### Phase 4: Test End-to-End
- User invokes Decision Council
- Verify tool calls happen
- Verify synthesis works
- User invokes Research Council
- Verify Task tool used
- Verify vault search works

**Total implementation: 1-2 days**

---

## Cost & Performance

### Fast Councils (query_persona_with_provider)
- 3 providers × ~500 tokens = 1500 tokens
- Haiku/GPT-mini/Gemini: ~$0.001 each
- **Total: ~$0.003-0.005 per council**
- **Speed: ~3-5 seconds** (parallel queries)

### Deep Councils (Task + subagents)
- 3 subagents × ~2000 tokens (with tools) = 6000 tokens
- Sonnet for depth: ~$0.008 per 1000 tokens
- **Total: ~$0.05-0.08 per council**
- **Speed: ~15-25 seconds** (sequential + tool calls)

**Same as before, but WAY simpler to implement!**

---

## Success Criteria

### Fast Councils
- [ ] User can invoke Decision Council
- [ ] Tool query_persona_with_provider gets called 3 times
- [ ] Responses come from different providers (Claude, GPT, Gemini)
- [ ] Synthesis follows template from skill
- [ ] Total time <5 seconds
- [ ] Total cost <$0.01

### Deep Councils
- [ ] User can invoke Research Council
- [ ] Task tool gets called for each subagent
- [ ] Subagents use vault_search and calendar_read
- [ ] Responses include vault citations
- [ ] Synthesis grounded in findings
- [ ] Total time <30 seconds
- [ ] Total cost <$0.10

### System
- [ ] No custom parsing code
- [ ] No custom routing code
- [ ] Council skills are pure markdown
- [ ] LLM reads and follows instructions
- [ ] New councils can be added via SQL insert

---

## Comparison: Parser-Based vs Tool-Based

| Aspect | Parser-Based (Old) | Tool-Based (New) |
|--------|-------------------|------------------|
| **Council skill format** | Rigid markdown structure | Freeform instructions |
| **Mode declaration** | `**Mode:** fast\|deep` | Implicit (which tools mentioned) |
| **Parsing logic** | Custom regex/markdown parser | None - LLM reads it |
| **Routing logic** | `if mode == "fast": ...` | None - LLM uses tools |
| **Execution** | Custom execute_fast/deep_council() | Tools (query_persona or Task) |
| **Lines of code** | ~500 | ~85 |
| **Complexity** | High (parsing, routing, executing) | Low (just tools) |
| **Flexibility** | Fixed structure | Any structure |
| **Debuggability** | Parse errors, routing bugs | Tool call trace |
| **Extensibility** | Add parsing rules | Just add tools |

**Tool-based wins on every dimension.**

---

## Open Questions for User Review

1. **Approve tool-based approach?**
   - Simpler, more flexible, fully aligned with skills
   - Requires LLM to follow instructions (already proven with skills)

2. **Tool naming?**
   - `query_persona_with_provider` vs `query_persona` vs `spawn_persona`?

3. **Council skill structure?**
   - Full freeform or suggest a template?
   - I recommend freeform but provide examples

4. **Ready to proceed with implementation?**
   - This replaces all previous phase 10 plans
   - Much simpler to implement (~2 days vs 3 weeks)

---

## What's Next

If approved:

**Day 1: Tool Implementation**
- Implement query_persona_with_provider
- Implement create_all_persona_subagents
- Wire up in chat endpoint
- Unit tests

**Day 2: Council Skills**
- Create Decision Council skill (fast)
- Create Research Council skill (deep)
- Create Creative Council skill (fast)
- Insert via SQL

**Day 3: Integration Testing**
- Test fast councils end-to-end
- Test deep councils end-to-end
- Test skill injection works
- Verify synthesis quality

**Day 4: Documentation & Deploy**
- User guide for councils
- How to create new councils (just write instructions!)
- Deploy to production

**Total: 4 days to production-ready system**

---

## Summary

**Core insight:** Council skills are instructions that the LLM reads and executes using tools, not data structures that get parsed.

**What changes:**
- ❌ Remove: All parsing and routing logic
- ✅ Add: One tool (query_persona_with_provider)
- ✅ Add: Subagent factory (create_all_persona_subagents)

**What stays the same:**
- ✅ Personas defined in database
- ✅ Persona skills defined in database
- ✅ Council skills defined in database
- ✅ Skill injection system (already works)

**Result:**
- 85 lines of code instead of 500+
- Fully flexible council definitions
- No custom parsing/routing
- Production-ready in 4 days

**This is the right architecture.** ✅
