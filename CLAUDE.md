# Second Brain System - Development Guide

**Project:** AI Second Brain System
**Location:** `~/dev/second-brain-app` (LOCAL - NOT iCloud!)
**Status:** Planning Phase - Scenario 3 MVP Implementation
**Last Updated:** 2025-12-23

**📋 Key Documentation:**
- **System Definition:** `docs/SYSTEM_DEFINITION_v0.9.md` - Complete spec
- **Comprehensive Review:** `docs/COMPREHENSIVE_REVIEW_2025-12-23.md` - Current state analysis
- **Implementation Plan:** `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md` - 4-week roadmap
- **Git + Docker Updates:** `docs/SCENARIO_3_UPDATES_GIT_DOCKER.md` - Latest changes

---

## Quick Reference

```bash
# Start dev servers
./scripts/dev.sh

# Tests (ALWAYS use uv run for Python)
cd services/brain_runtime && uv run pytest
cd apps/web && pnpm test

# Lint
cd services/brain_runtime && uv run ruff check .
cd apps/web && pnpm lint

# Health check
curl http://localhost:8000/health
```

**Critical Python Rules:**
- ✅ Always use `uv run <command>` (uses project .venv with Python 3.11.10)
- ❌ Never use bare `pytest` or `python` (may use wrong environment)
- ❌ Never use `uv pip list` (queries conda, not .venv)
- See `docs/COMPREHENSIVE_REVIEW_2025-12-23.md` for Python environment details

---

## Current Status

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| **Phases 1-9A** | ✅ Complete | ~20% | Foundation, Chat, Proposals, Skills |
| **Phase 10** | ⚠️ 90% | <5% | Personas/Councils - needs verification |
| **Scenario 3** | 📋 Planned | Target: 70% | 4-week MVP plan ready |

**Critical Gaps:**
- Test coverage: <5% (target: 70%)
- Docker: Not implemented (Week 3)
- Git workflow: Not integrated (Week 1 + Week 2)
- Error handling: Inconsistent

**Current Focus:** Scenario 3 implementation plan finalized, ready to begin Week 1

---

## Git Workflow (NEW - Week 1 & 2)

### Application Git (Week 1, Day 5)
**Purpose:** Version control the codebase itself

```bash
# Initialize and push to GitHub
git init
git add .
git commit -m "Initial commit: Second Brain v0.9"
gh repo create second-brain-app --private --source=. --remote=origin
git push -u origin main
```

**Key files:**
- `.gitignore` - Excludes secrets, data, logs, build artifacts
- Development branch for experiments
- GitHub as source of truth for code

### Vault Git Management (Week 2, Day 7)
**Purpose:** UI-driven git for Obsidian vault with auto-commit on edits

**Features:**
- Health dashboard showing vault git status
- Auto-commit before/after proposal apply
- Manual "Commit & Push" button
- Configurable auto-push (default: off)

**UX:**
```
Proposal Apply Flow:
1. Pre-edit commit: "Pre-edit: {proposal_title}"
2. Apply file changes
3. Post-edit commit: "[Second Brain] Applied: {proposal_title}"
4. Optional auto-push to GitHub
```

**Settings:**
- `auto_commit_on_edit` (default: true) - Safety checkpoint
- `auto_push` (default: false) - Push after commit
- `commit_message_template` - Custom format

See `docs/SCENARIO_3_UPDATES_GIT_DOCKER.md` for complete implementation details.

---

## Docker Deployment (Week 3)

**Critical Fix Applied:** Vault must be mounted **read-write** (not read-only) for proposals to work.

```yaml
# docker-compose.yml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault"  # ✅ Read-write (proposals need this!)
  - backend_data:/app/data
```

**File Permissions Fix:**
```dockerfile
# Dockerfile - runs as non-root user matching host UID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} app && useradd -u ${USER_ID} -g app app
USER app
```

**Services:**
- Frontend (Next.js) - Port 3000
- Backend (FastAPI) - Port 8000
- PostgreSQL 16 - Port 5432 (internal)
- ChromaDB - Port 8001 (internal)

**Commands:**
```bash
./scripts/docker-build.sh    # Build images
./scripts/docker-start.sh    # Start all services
./scripts/docker-logs.sh     # View logs
./scripts/docker-stop.sh     # Stop services
```

See `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md` (Day 15) for complete Docker setup.

---

## Phase 10: Council & Persona System (90% Complete)

**Concept:** Rotate coaching personalities with exclusive skills using tool-based architecture.

**Status:**
- ✅ Backend: query_persona_with_provider tool, subagent factory, API endpoints
- ✅ Database: 5 personas seeded (Socratic, Contrarian, Pragmatist, Synthesizer, Coach)
- ✅ Skills: 8 persona-specific + 3 council skills
- ⚠️ Integration: Needs verification (chat wiring, frontend, session tracking)
- ❌ Tests: 0% coverage

**Personas:**
| Name | Icon | Style |
|------|------|-------|
| Socratic | 🏛️ | Questions assumptions |
| Contrarian | 😈 | Finds weaknesses |
| Pragmatist | 🎯 | Drives to action |
| Synthesizer | 🔮 | Finds connections |
| Coach | 🌱 | Supportive growth |

**Architecture:** Tool-based (LLM reads skills as instructions, not parsed data)

Full details: `docs/SYSTEM_DEFINITION_v0.9.md` (Phase 10 section)

---

## Claude Models

| Model | ID | Context | Price (in/out) |
|-------|-----|---------|----------------|
| **Opus 4.5** | `claude-opus-4-5-20251101` | 200K | $5/$25 per M |
| **Sonnet 4.5** | `claude-sonnet-4-5-20250929` | 200K (1M beta) | $3/$15 per M |
| **Haiku 4.5** | `claude-haiku-4-5-20251001` | 200K | $1/$5 per M |

**Usage:** Orchestrator → Sonnet 4.5 | Council → Haiku 4.5 | Synthesis → Opus

**Beta Headers:**
```python
["prompt-caching-2024-07-31", "extended-cache-ttl-2025-04-11", "token-efficient-tools-2025-02-19"]
```

---

## Database Schema

**Core Tables (17):**
- Jobs, Calendar, Tasks (Phases 1-4)
- Chat, Skills, Proposals (Phases 7-9)
- Sync, Settings, Modes, Commands (Phase 9A)

**Phase 10 Extensions:**
```sql
-- Personas in modes table
ALTER TABLE modes ADD COLUMN is_persona BOOLEAN;
ALTER TABLE modes ADD COLUMN can_orchestrate BOOLEAN;
ALTER TABLE modes ADD COLUMN persona_config JSONB;

-- Skills scoped to personas
ALTER TABLE user_skills ADD COLUMN persona_ids TEXT[];

-- Session tracking
ALTER TABLE chat_sessions ADD COLUMN lead_persona_id UUID;
ALTER TABLE chat_sessions ADD COLUMN council_member_ids TEXT[];
```

**Week 2 Extensions (Git):**
```sql
-- Vault git settings
ALTER TABLE user_settings ADD COLUMN git_settings JSONB DEFAULT '{
  "auto_commit_on_edit": true,
  "auto_push": false
}'::jsonb;
```

---

## API Endpoints

**Core:**
- `/health`, `/config`, `/jobs/*`, `/vault/*`, `/calendar/*`, `/tasks/*`

**Chat & Agent:**
- `POST /chat` - SSE streaming
- `/chat/sessions/*`, `/agent/runs/*`

**Phase 8-9:**
- `/proposals/*`, `/skills/*`, `/settings/*`, `/modes/*`, `/commands/*`

**Phase 10:**
- `/personas/*` - List personas
- `/personas/{id}/skills` - Persona skills
- `/councils/*` - Council metadata

**Week 2 (Git):**
- `GET /vault/git/status` - Current git status
- `POST /vault/git/sync` - Commit & push
- `GET /vault/git/diff` - View changes

---

## Project Structure

```
second-brain-app/
  apps/web/                   # Next.js 15 (App Router)
    src/
      app/                    # Pages (chat, settings, health)
      components/             # UI components
        chat/                 # MessageBubble, ChatInput, CouncilResponse
        modes/                # PersonaChip, NewChatModal
        health/               # VaultGitCard, SystemStatsCard (Week 2)
  services/brain_runtime/     # FastAPI
    api/                      # Route handlers
    core/
      git_service.py          # Vault git operations (Week 2)
      tools/
        persona_query.py      # query_persona_with_provider (Phase 10)
    migrations/
      005_persona_council.sql # Phase 10 schema
  docs/                       # Comprehensive documentation
    SYSTEM_DEFINITION_v0.9.md
    SCENARIO_3_IMPLEMENTATION_PLAN.md
    SCENARIO_3_UPDATES_GIT_DOCKER.md
```

**External Paths:**
- Vault: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian-Private`
- Skills: `~/.claude/skills/` (39+ skills)

---

## Development Guidelines

### Python (FastAPI Backend)
- Package manager: `uv` (always use `uv run`)
- Python version: 3.11 (strict)
- Database: PostgreSQL + asyncpg + SQLAlchemy 2.0
- Testing: pytest + pytest-asyncio
- Linting: ruff

### TypeScript (Next.js Frontend)
- Package manager: `pnpm`
- Framework: Next.js 15 (App Router)
- Validation: Zod
- Data fetching: React Query
- Styling: Tailwind CSS

### Testing Strategy (Scenario 3 Target: 70%)
- **Unit:** Tools, parsers, utilities
- **Integration:** API endpoints, database operations, git operations
- **E2E (Playwright):** Full user flows

### Security
- Path sandboxing: All vault operations validated
- Secrets: `data/secrets/` (gitignored)
- API keys: Encrypted in database
- CORS: Restricted to localhost (production)

---

## Environment

```bash
# Required
OBSIDIAN_VAULT_PATH=...              # Vault path (quote if spaces)
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://...

# Optional (Phase 10 multi-vendor)
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...

# Calendar sync
CALENDAR_WORK_URL=...                # M365 ICS
CALENDAR_PRIVATE_URL=...             # Google ICS

# Encryption
API_KEY_ENCRYPTION_KEY=...           # Fernet key

# Docker (Week 3)
USER_ID=1000                         # Run `id -u`
GROUP_ID=1000                        # Run `id -g`
```

PostgreSQL: `localhost:5432/second_brain`

---

## Skills System

**Progressive Disclosure:**
- Level 1: Metadata (~100 tokens) - Always loaded
- Level 2: Instructions (<5K tokens) - Loaded when triggered
- Level 3: Resources (0 tokens) - Accessed via filesystem

**Categories:** knowledge, workflow, analysis, creation, integration, training, productivity, **council** (Phase 10)

**Persona Scoping (Phase 10):**
- `persona_ids = NULL` → Universal (all personas)
- `persona_ids = ["uuid"]` → Exclusive to persona

**Location:** `~/.claude/skills/` or vault `.claude/agents/`

---

## Scenario 3 Roadmap (4 Weeks, 113 Hours)

**Week 1: Critical Path (5 days)**
- Day 1: Python environment + linters ✅
- Day 2: Phase 10 verification
- Day 3-4: Core test suite (25%)
- Day 5: Security + Git setup + Beta deploy

**Week 2: Monitoring + Git + Testing (5 days)**
- Day 6: Usage monitoring + bug fixes
- **Day 7: Health Dashboard + Vault Git** ⭐
- Day 8-9: Backend tests (40%)
- Day 10: Frontend tests (30%)

**Week 3: Full Coverage + Docker (5 days)**
- Day 11-13: Expand tests to 70%
- Day 14: Error boundaries + retry logic
- **Day 15: Docker implementation** 🐳

**Week 4: Performance + Polish (5 days)**
- Day 16-17: Optimize queries, caching, bundle size
- Day 18: Documentation pass
- Day 19: Final integration tests
- Day 20: Production deploy

**Deliverables:**
- ✅ 70% test coverage
- ✅ Docker deployment ready
- ✅ Git workflow integrated (app + vault)
- ✅ Solid MVP for daily use

See `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md` for day-by-day breakdown.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Python version error | `uv run python --version` → should be 3.11.10 |
| Pydantic import error | Use `uv run pytest` not bare `pytest` |
| Tests can't collect | Ensure dev dependencies installed: `uv sync --extra dev` |
| PostgreSQL fails | `pg_isready`, check DB is running |
| iCloud slow/hangs | Project MUST be in `~/dev/`, NOT iCloud |
| Vault read-only (Docker) | Fixed in plan - mount as read-write |
| Files owned by root (Docker) | Fixed in plan - use USER_ID/GROUP_ID |

---

## Key Principles

1. **Local-first:** Runs on MacBook, vault is source of truth
2. **Contracts-first:** Versioned schemas for all data
3. **Safety:** Read-only default, writes require approval (or YOLO mode)
4. **Progressive disclosure:** Load minimal context, deepen on demand
5. **Cognitive diversity:** Personas provide different reasoning styles
6. **Git safety:** Auto-commit before/after vault edits (Week 2)
7. **Honest documentation:** Status reflects reality, not aspirations
8. **Python 3.11 only:** Strict version enforcement via uv
9. **Building for personal use:** MVP quality, not enterprise scale

---

## What's Next?

**Ready to implement:** All planning complete, specs finalized.

**Start here:**
1. Review `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md`
2. Begin Week 1, Day 1: Python environment verification
3. Follow day-by-day plan to solid MVP

**Questions?** Check documentation links at top of this file.

**Critical reminders:**
- Always use `uv run` for Python commands
- Vault in Docker must be read-write (not `:ro`)
- Git workflow adds safety for all edits
- Target: 70% test coverage by end of Week 3
