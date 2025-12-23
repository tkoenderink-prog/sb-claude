# Day 1: Python Environment & Linter Fix

**Date:** 2025-12-23
**Status:** ✅ Complete
**Scenario:** Week 1, Day 1 of [Scenario 3 Implementation Plan](SCENARIO_3_IMPLEMENTATION_PLAN.md)

---

## Summary

Fixed Python environment, dependency management, and all linter warnings. Environment now correctly uses project `.venv` with Python 3.11.10. All linters pass, tests can run (6 failures are database logic issues, not environment issues).

---

## What Was Done

### 1. Python Environment Fix

**Problem:** Tests failing with Pydantic import errors
```
ImportError: cannot import name 'AliasGenerator' from 'pydantic'
```

**Root Cause:** `pytest` was not installed in the project `.venv`, so `uv run pytest` was falling back to global Python environment which had incompatible Pydantic versions.

**Solution:**
1. Added `[project.optional-dependencies]` section to `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   dev = [
       "pytest>=7.4.4",
       "pytest-asyncio>=0.21.1",
       "pytest-cov>=4.1.0",
       "pytest-timeout>=2.4.0",
       "ruff>=0.1.0",
   ]
   ```

2. Installed dev dependencies:
   ```bash
   uv sync --extra dev
   ```

3. Added pytest configuration to `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["."]
   python_files = ["test_*.py"]
   ```

**Result:** Tests now run with correct Python environment (3.11.10 from `.venv`)

---

### 2. Python Linter Fix

**Ran:** `uv run ruff check . --fix`

**Fixed Automatically (8 errors):**
- Removed unused imports in `api/context_files.py`, `api/personas.py`, `api/proposals.py`, `api/settings.py`
- Removed unused imports in `core/proposal_service.py`, `core/token_counter.py`, `core/tools/proposal_tools.py`
- Removed unused import in `test_skills_fix.py`

**Fixed Manually (4 errors):**
1. **Boolean comparison in `api/personas.py` (3 instances):**
   - Changed: `ModeDB.is_persona == True` → `ModeDB.is_persona`
   - Lines: 63, 101, 145

2. **Import order in `core/database.py`:**
   - Moved `from contextlib import asynccontextmanager` to top of file
   - Removed duplicate import on line 57

**Result:** `ruff check .` → ✅ All checks passed!

---

### 3. TypeScript Linter Fix

**Problem:** Missing dependency warning in `apps/web/src/hooks/useChat.ts:295`
```
React Hook useCallback has a missing dependency: 'sessionTitle'
```

**Solution:**
Changed dependency array from `[sessionId]` to `[sessionId, sessionTitle]`

**Result:** `pnpm lint` → ✅ No ESLint warnings or errors

---

### 4. Test Suite Status

**Command:** `uv run pytest -v`

**Results:**
- ✅ 2 passed
- ❌ 6 failed (database logic issues, not environment)

**Passing Tests:**
- `test_providers.py::test_providers`
- `test_skills_fix.py::test_list_skills_with_source_filter`

**Failing Tests** (database issues):
- `test_sdk_integration.py::test_sdk_runtime` - SQL type casting error
- `test_skills_fix.py::test_list_skills_with_none_parameters` - Database concurrency
- `test_skills_fix.py::test_list_skills_with_category_filter` - SQL type error
- `test_skills_fix.py::test_search_skills` - Database concurrency
- `test_skills_fix.py::test_get_skills_stats` - Database concurrency
- `test_skills_fix.py::test_tool_function_integration` - Database concurrency

**Note:** Failures are due to:
1. PostgreSQL type casting issues (`text[] ~~ text` operator)
2. Database connection management (concurrent operations)

These will be addressed in Week 2 when expanding test coverage.

---

## Python Environment Behavior (Final Clarification)

### The Three Environments

| Command | Python Version | Path | Notes |
|---------|----------------|------|-------|
| `python` | 3.11.13 | Shell alias | System Python (pyenv) |
| `uv run python` | 3.11.10 | `.venv/bin/python3` | ✅ Project environment (CORRECT) |
| `uv pip list` | 3.12.4 | `/opt/miniconda3` | ❌ Queries conda (WRONG) |

### ✅ Correct Usage

**Always use `uv run <command>` for Python operations:**
```bash
uv run python --version      # 3.11.10 from .venv
uv run pytest                # Uses .venv pytest
uv run ruff check .          # Uses .venv ruff
uv run uvicorn main:app      # Uses .venv uvicorn
```

### ❌ Avoid These

**Don't use bare commands:**
```bash
pytest                       # May use wrong environment
python test_something.py     # Uses system Python
ruff check .                 # Uses system ruff
```

**Don't use `uv pip` for inspection:**
```bash
uv pip list                  # Queries conda environment (wrong!)
```

### Why This Matters

`uv run` ensures:
1. Correct Python version (3.11.10)
2. Correct dependencies (Pydantic 2.12.5+, pytest, etc.)
3. Isolated environment (no conda conflicts)

---

## Files Modified

### Backend (`services/brain_runtime/`)
- ✅ `pyproject.toml` - Added dev dependencies + pytest config
- ✅ `api/personas.py` - Fixed boolean comparisons
- ✅ `core/database.py` - Fixed import order

### Frontend (`apps/web/`)
- ✅ `src/hooks/useChat.ts` - Fixed useCallback dependency

---

## Deliverables

1. ✅ Python environment working correctly
2. ✅ All linter warnings fixed (Python + TypeScript)
3. ✅ Tests can run (2/8 passing, 6 have database issues)
4. ✅ Documentation of Python environment behavior

---

## Next Steps (Scenario 3, Week 1)

According to [SCENARIO_3_IMPLEMENTATION_PLAN.md](SCENARIO_3_IMPLEMENTATION_PLAN.md):

**Day 2: Verify Phase 10 Integration (4 hours)**
- Check if personas are wired into chat
- Verify council skills work
- Test `query_persona_with_provider` tool
- Document what's working vs. missing

**Day 3-5: Core Test Suite (12 hours)**
- Fix database concurrency issues
- Add unit tests for tools, skills, proposals
- Add integration tests for councils
- Target: 25% coverage by end of week

---

## Lessons Learned

1. **Always add test dependencies to pyproject.toml** - Don't rely on global installs
2. **uv run is mandatory** - Never use bare Python commands
3. **pytest needs explicit asyncio config** - Add `asyncio_mode = "auto"`
4. **Ruff can auto-fix most issues** - Use `--fix` flag first
5. **Environment verification first** - Before any coding, verify tools work

---

**Status:** Day 1 Complete ✅
**Time Spent:** ~2 hours
**Next:** Day 2 - Phase 10 Verification
