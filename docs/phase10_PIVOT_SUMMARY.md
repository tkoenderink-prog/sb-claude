# Phase 10: Tool-Based Architecture Pivot - EXECUTE THIS

**Date:** 2025-12-23
**Decision:** DELETE parser-based code, implement tool-based architecture
**Timeline:** 4 days to production

---

## What Happened

After implementing comprehensive documentation for **tool-based councils**, the codebase was found to contain a **completely different parser-based implementation**. This created:

- ❌ Architectural inconsistency (docs vs code divergence)
- ❌ Technical debt (500+ lines of parsing/orchestration code)
- ❌ Higher costs (no prompt caching, $0.055 vs $0.02 per council)
- ❌ Less flexibility (rigid structure vs freeform markdown)

**Decision:** Delete parser-based code and implement tool-based architecture as documented.

---

## Three Key Documents

1. **`phase10_tool_based_councils_executive_summary.md`** (1,016 lines)
   - Complete reasoning: Why tool-based > parser-based
   - Architecture overview
   - Cost analysis: 65% savings via prompt caching
   - 95% confidence in decision

2. **`phase10_tool_based_councils_implementation_plan.md`** (1,472 lines)
   - Complete code implementations (query_persona_with_provider + subagent factory)
   - 3 example council skills with full SQL (Decision, Research, Creative)
   - Comprehensive testing strategy
   - 4-day deployment plan

3. **`phase10_pivot_to_tool_based.md`** (THIS PLAN)
   - Phase-by-phase pivot execution
   - Code deletion checklist
   - Implementation roadmap
   - Validation criteria

---

## What Gets Deleted

### Files to DELETE Entirely:
- `services/brain_runtime/core/tools/council_tool.py` (invoke_council tool)

### Functions to DELETE from Existing Files:
- `core/council.py`: `parse_council_skill()`, `execute_council()`, dataclasses
- `api/councils.py`: `POST /councils/{name}/invoke` endpoint

### Database:
- Delete old parser-based Decision Council skill

**Total deletion: ~500 lines of parser-based code**

---

## What Gets Implemented

### New Files (85 lines total):
1. `core/tools/persona_query.py` (~50 lines)
   - `query_persona_with_provider(persona_name, provider, query)` tool
   - Queries personas via LiteLLM (anthropic/openai/google)

2. `core/persona_subagents.py` (~30 lines)
   - `create_all_persona_subagents(db)` factory
   - Returns dict of AgentDefinition for deep councils

3. `core/multi_llm.py` (config)
   - Provider model mappings
   - LiteLLM configuration

### Modified Files:
4. `core/council.py` - Add helper functions:
   - `get_all_personas()`
   - `get_council_skill_by_name()`

5. `api/chat.py` - Wire in subagents:
   - Create subagents on chat start
   - Add to ClaudeAgentOptions
   - Enable Task tool + query_persona_with_provider

### Database:
6. Insert 3 tool-based council skills:
   - Decision Council (fast) - Uses query_persona_with_provider
   - Research Council (deep) - Uses Task tool with subagents
   - Creative Council (fast) - Uses query_persona_with_provider

---

## Execution Order

### Phase 1: Delete Parser-Based Code (2 hours)

See `phase10_DELETE_PARSER_CODE.md` for detailed checklist.

```bash
# Backup
git stash push -m "Pre-pivot backup: parser-based council code"

# Delete
rm services/brain_runtime/core/tools/council_tool.py

# Edit council.py (remove parse/execute functions)
# Edit councils.py (remove POST /councils/{name}/invoke)

# Delete old council skills
psql -d second_brain -c "DELETE FROM user_skills WHERE name = 'Decision Council' AND category = 'council';"

# Verify
grep -r "parse_council" services/brain_runtime --exclude-dir=__pycache__
# Should return NO results

# Commit
git add -A
git commit -m "refactor(phase10): Delete parser-based council code"
```

### Phase 2: Implement Tool-Based Core (Day 1)

**Morning (4 hours):**
1. Create `core/tools/persona_query.py`
   - Copy implementation from `phase10_tool_based_councils_implementation_plan.md` lines 72-207
   - Add LiteLLM dependency: `cd services/brain_runtime && uv add litellm`

2. Create `core/persona_subagents.py`
   - Copy implementation from plan lines 269-372

3. Update `core/council.py`
   - Add `get_all_personas()` function
   - Add `get_council_skill_by_name()` function

**Afternoon (4 hours):**
4. Create `core/multi_llm.py`
   - Copy implementation from plan lines 211-260

5. Update `api/chat.py`
   - Import `create_all_persona_subagents`
   - Create subagents before ClaudeAgentOptions
   - Add to options: `agents=subagents`, `allowed_tools=["Task", "query_persona_with_provider", ...]`

6. Run tests:
   ```bash
   cd services/brain_runtime
   uv run pytest tests/test_persona_query_tool.py
   uv run pytest tests/test_persona_subagents.py
   ```

### Phase 3: Council Skills (Day 2)

**Morning (4 hours):**
1. Insert Decision Council (fast)
   - Copy SQL from `phase10_pivot_to_tool_based.md` lines 326-408

2. Insert Research Council (deep)
   - Copy SQL from plan lines 410-506

3. Insert Creative Council (fast)
   - Copy SQL from plan lines 508-588

**Afternoon (4 hours):**
4. Manual testing:
   ```bash
   # Start servers
   ./scripts/dev.sh

   # Create chat with Socratic as lead
   # Ask: "Should I quit my job? Invoke Decision Council."
   # Verify: Three tool calls to query_persona_with_provider
   # Verify: Responses from anthropic, openai, google
   # Verify: Synthesis follows template
   ```

5. Integration tests:
   ```bash
   cd services/brain_runtime
   uv run pytest tests/test_council_integration.py -v
   ```

### Phase 4: Polish & Deploy (Day 3)

**Morning (3 hours):**
1. Fix lint errors:
   ```bash
   cd services/brain_runtime && uv run ruff check . --fix
   ```

2. Update CLAUDE.md ✅ (Already done)

3. Create PR or commit:
   ```bash
   git add -A
   git commit -m "feat(phase10): Implement tool-based council architecture

   - Add query_persona_with_provider tool (fast councils)
   - Add persona subagent factory (deep councils)
   - Add 3 council skills (Decision, Research, Creative)
   - LiteLLM integration for multi-provider support
   - 85 lines of code vs 500+ in parser-based

   Cost: $0.02 per council (65% savings via prompt caching)

   See docs/phase10_pivot_to_tool_based.md for full plan."
   ```

**Afternoon (2 hours):**
4. Deploy to production
5. Smoke test all three councils
6. Monitor logs for errors

---

## Success Criteria

### Code Metrics:
- [ ] Parser-based code deleted (~500 lines removed)
- [ ] Tool-based code implemented (~85 lines added)
- [ ] Net reduction: 415 lines (83% less code)

### Functionality:
- [ ] Decision Council works (fast, multi-provider)
- [ ] Research Council works (deep, vault search)
- [ ] Creative Council works (fast, multi-provider)

### Cost:
- [ ] Prompt caching enabled (90% savings)
- [ ] Cost per council: $0.02 (vs $0.055 without caching)

### Quality:
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Lint errors: 0
- [ ] Build check: SUCCESS

---

## Environment Variables

Add to `.env`:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (for multi-provider councils)
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...
```

Check setup:
```bash
cd services/brain_runtime
uv run python -c "
from core.multi_llm import get_available_providers
print('Available providers:', get_available_providers())
"
```

---

## Rollback Plan

If something breaks:

```bash
# Restore parser-based code
git stash pop

# Or revert commits
git revert HEAD~3..HEAD

# Or checkout specific commit
git checkout <commit-before-pivot>
```

---

## Post-Pivot Cleanup

Once tool-based is working:

1. Archive parser-based docs (if any exist)
2. Update developer guide with tool-based examples
3. Remove any stale comments referencing parser approach
4. Run full E2E test suite
5. Update Phase 10 status in CLAUDE.md to "Complete"

---

## Key Principles

**Why tool-based is correct:**

1. **Skills are instructions** - The LLM reads them, doesn't parse them
2. **Claude SDK handles orchestration** - We don't maintain it
3. **Prompt caching works** - 90% cost savings
4. **Freeform structure** - Any markdown format works
5. **Minimal code** - 85 lines vs 500+

**This is the architecture we build from now on.**

---

## Timeline

| Day | Phase | Tasks | Hours |
|-----|-------|-------|-------|
| **1** | Delete + Core | Delete parser code, implement tools, subagents | 8 |
| **2** | Skills + Test | Insert 3 councils, manual testing, integration tests | 8 |
| **3** | Polish + Deploy | Fix lint, commit, deploy, smoke test | 5 |
| **4** | Buffer | Handle any issues, final verification | 4 |

**Total: 25 hours over 4 days**

---

## Next Steps

**Start immediately:**

1. Read `phase10_DELETE_PARSER_CODE.md`
2. Execute deletion checklist
3. Verify no parser-based code remains
4. Implement tool-based architecture per `phase10_pivot_to_tool_based.md`
5. Test thoroughly
6. Deploy to production

**No more parser-based code after this.**

---

**END OF PIVOT SUMMARY**

Ready to execute. Let's build it right this time.
