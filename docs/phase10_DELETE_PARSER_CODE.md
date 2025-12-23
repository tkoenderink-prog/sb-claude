# Phase 10: Parser-Based Code Deletion Plan

**Status:** READY TO EXECUTE
**Date:** 2025-12-23

## Files to DELETE Entirely

### 1. `/services/brain_runtime/core/tools/council_tool.py`
**Reason:** Contains `invoke_council` tool that uses parser-based approach.
**Replaced by:** LLM reading council skill instructions and calling `query_persona_with_provider` directly.

**Delete command:**
```bash
rm /Users/tijlkoenderink/dev/second-brain-app/services/brain_runtime/core/tools/council_tool.py
```

---

## Files to MODIFY (Remove Parser-Based Functions)

### 2. `/services/brain_runtime/core/council.py`

**Functions to DELETE:**
- `parse_council_skill()` (line ~56) - Parses markdown into CouncilDefinition
- `execute_council()` (line ~127) - Parser-based council execution
- `CouncilDefinition` dataclass - Structured council representation
- `MemberConfig` dataclass - Parsed member configuration

**Functions to KEEP:**
- `get_persona_by_name()` - Used by query_persona_with_provider tool
- `get_persona_by_id()` - Used by chat integration
- `get_skill_by_name()` - Generic skill lookup (used for loading council skills)
- `resolve_personas_by_name()` - Used for member resolution

**Functions to ADD:**
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

---

### 3. `/services/brain_runtime/api/councils.py`

**Endpoint to DELETE:**
- `POST /councils/{name}/invoke` (line 135-206) - Manual council invocation endpoint

**Why:** Councils are invoked automatically by LLM reading skills and calling tools, not via POST endpoint.

**Endpoints to KEEP:**
- `GET /councils` (list all council skills) - Still useful for UX to show available councils
- `GET /councils/{name}` (get council details) - Still useful for skill metadata

**Imports to REMOVE after deletion:**
- `parse_council_skill` (no longer needed)
- `execute_council` (no longer needed)
- `CouncilInvokeRequest`, `CouncilMemberResponse`, `CouncilInvokeResponse` Pydantic models

---

## Database Changes

### 4. Delete Parser-Based Council Skills

```sql
-- Remove Decision Council with parser-based format
DELETE FROM user_skills
WHERE name = 'Decision Council'
  AND category = 'council'
  AND content LIKE '%## Members%';  -- Only delete parser-based format
```

**Note:** If there are no council skills yet, skip this step.

---

## Verification Commands

After deletion, verify no parser-based references remain:

```bash
cd /Users/tijlkoenderink/dev/second-brain-app/services/brain_runtime

# Should return NO results
grep -r "parse_council_skill" . --exclude-dir=__pycache__ --exclude-dir=.venv
grep -r "execute_council" . --exclude-dir=__pycache__ --exclude-dir=.venv
grep -r "CouncilDefinition" . --exclude-dir=__pycache__ --exclude-dir=.venv
grep -r "invoke_council" . --exclude-dir=__pycache__ --exclude-dir=.venv

# This is OK (council.py will have these helper functions)
grep -r "get_persona_by_name" . --exclude-dir=__pycache__ --exclude-dir=.venv
grep -r "get_all_personas" . --exclude-dir=__pycache__ --exclude-dir=.venv
```

---

## Import Cleanup

After deleting code, check for broken imports:

```bash
cd services/brain_runtime
uv run python -c "
from core.council import get_persona_by_name, get_persona_by_id, get_skill_by_name
from core.skill_loader import load_skills_for_persona, build_persona_system_prompt
from api.councils import router
print('All imports successful')
"
```

---

## Order of Operations

1. **Backup current code** (just in case):
   ```bash
   cd /Users/tijlkoenderink/dev/second-brain-app
   git stash push -m "Pre-pivot backup: parser-based council code"
   ```

2. **Delete council_tool.py:**
   ```bash
   rm services/brain_runtime/core/tools/council_tool.py
   ```

3. **Edit council.py:**
   - Delete `parse_council_skill()` function
   - Delete `execute_council()` function
   - Delete `CouncilDefinition` and `MemberConfig` dataclasses
   - Add `get_all_personas()` function
   - Add `get_council_skill_by_name()` function

4. **Edit councils.py:**
   - Delete `POST /councils/{name}/invoke` endpoint
   - Remove imports: `parse_council_skill`, `execute_council`
   - Remove Pydantic models: `CouncilInvokeRequest`, `CouncilMemberResponse`, `CouncilInvokeResponse`

5. **Delete old council skills from database:**
   ```bash
   psql -d second_brain -c "DELETE FROM user_skills WHERE name = 'Decision Council' AND category = 'council' AND content LIKE '%## Members%';"
   ```

6. **Run verification commands** (see above)

7. **Fix lint errors:**
   ```bash
   cd services/brain_runtime
   uv run ruff check . --fix
   ```

8. **Commit deletion:**
   ```bash
   git add -A
   git commit -m "refactor(phase10): Delete parser-based council code, prepare for tool-based implementation

- DELETE: core/tools/council_tool.py (invoke_council tool)
- DELETE: parse_council_skill(), execute_council() from core/council.py
- DELETE: POST /councils/{name}/invoke endpoint from api/councils.py
- DELETE: CouncilDefinition, MemberConfig dataclasses
- ADD: get_all_personas(), get_council_skill_by_name() to core/council.py
- Database: Delete old parser-based Decision Council skill

Rationale: Pivot to tool-based architecture where LLM reads council skills
as natural language instructions and calls tools directly. No parsing required.

See docs/phase10_pivot_to_tool_based.md for implementation plan."
   ```

---

## Post-Deletion Checklist

- [ ] council_tool.py deleted
- [ ] parse_council_skill() removed from council.py
- [ ] execute_council() removed from council.py
- [ ] CouncilDefinition dataclass removed
- [ ] MemberConfig dataclass removed
- [ ] POST /councils/{name}/invoke removed from councils.py
- [ ] get_all_personas() added to council.py
- [ ] get_council_skill_by_name() added to council.py
- [ ] Old council skills deleted from database
- [ ] No grep results for "parse_council_skill"
- [ ] No grep results for "execute_council"
- [ ] No grep results for "CouncilDefinition"
- [ ] Build check passes
- [ ] Lint errors fixed
- [ ] Committed with clear message

---

## What Happens Next

After deletion is complete:

1. **Implement tool-based architecture** (see `phase10_pivot_to_tool_based.md`)
2. **Create persona_query.py** (query_persona_with_provider tool)
3. **Create persona_subagents.py** (AgentDefinition factory)
4. **Update chat integration** (wire in subagents)
5. **Insert tool-based council skills** (Decision, Research, Creative)
6. **Test end-to-end** (manual + automated)

**Estimated time:** 4 days to fully functional tool-based system.

---

**This deletion must happen before implementing tool-based architecture.**
**No parser-based code should remain after this.**
