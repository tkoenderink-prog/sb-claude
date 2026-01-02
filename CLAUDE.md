# Second Brain System - Development Guide

**Project:** AI Second Brain System (sb-claude)
**Location:** `/Users/tijlkoenderink/Library/Mobile Documents/iCloud~md~obsidian/Documents/web-sb-claude`
**Vault:** `/Users/tijlkoenderink/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian-Private`
**Status:** ⚡ **DEVELOPMENT CYCLE IN PROGRESS** - Production Readiness Phase
**Last Updated:** 2026-01-02

**📋 Key Documentation:**
- **Development Cycle Plan:** `DEVELOPMENT-CYCLE-PLAN.md` - 7-phase roadmap to production (NEW!)
- **Next Phase Roadmap:** `2do-next-phase.md` - Post-production features (NEW!)
- **Setup Guide:** `SETUP.md` - Complete setup instructions (NEW!)
- **System Definition:** `docs/SYSTEM_DEFINITION_v0.9.md` - Complete spec
- **Comprehensive Review:** `docs/COMPREHENSIVE_REVIEW_2025-12-23.md` - Current state analysis
- **Implementation Plan:** `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md` - 4-week roadmap
- **Git + Docker Updates:** `docs/SCENARIO_3_UPDATES_GIT_DOCKER.md` - Latest changes

---

## Development Modes

Two development modes available - use different ports to tell them apart:

| Service | Docker Mode | Local Mode |
|---------|-------------|------------|
| Frontend | **3000** | **3001** |
| Backend | **8000** | **8001** |
| PostgreSQL | 5432 (shared) | 5432 (shared) |
| ChromaDB | 8002 (shared) | 8002 (shared) |

### Quick Start

```bash
# OPTION 1: Local Development (fastest iteration)
./scripts/dev-local.sh
# Frontend: http://localhost:3001
# Backend:  http://localhost:8001

# OPTION 2: Docker Development (production-like)
./scripts/dev-docker.sh
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000

# Infrastructure only (PostgreSQL + ChromaDB)
./scripts/infra.sh

# Stop everything
./scripts/infra-stop.sh
```

### When to Use Each Mode

**Local Mode (`./scripts/dev-local.sh`)** - Daily development
- ✅ Fastest hot reload (native filesystem)
- ✅ Easy debugging with IDE
- ✅ No container rebuild needed
- ⚠️ Requires local Python 3.11 + Node 20

**Docker Mode (`./scripts/dev-docker.sh`)** - Testing/verification
- ✅ Identical to production
- ✅ No local dependencies needed
- ✅ Test Docker-specific behavior
- ⚠️ Slower hot reload on macOS

### Health Dashboard

Visit `/health` to see environment info:
- Environment badge shows 🐳 Docker or 💻 Local
- Environment card shows ports, mode, ChromaDB connection
- Both modes can run simultaneously on different ports!

---

## Quick Reference

```bash
# Tests (ALWAYS use uv run for Python)
cd services/brain_runtime && uv run pytest
cd apps/web && pnpm test

# Lint
cd services/brain_runtime && uv run ruff check .
cd apps/web && pnpm lint

# Health check
curl http://localhost:8000/health  # Docker
curl http://localhost:8001/health  # Local
```

**Critical Python Rules:**
- ✅ Always use `uv run <command>` (uses project .venv with Python 3.11.10)
- ❌ Never use bare `pytest` or `python` (may use wrong environment)
- ❌ Never use `uv pip list` (queries conda, not .venv)
- See `docs/COMPREHENSIVE_REVIEW_2025-12-23.md` for Python environment details

---

## Current Status

**🎯 NEW: Development Cycle Initiated (2026-01-02)**

We are now executing a comprehensive 7-phase development cycle to achieve production readiness:

| Phase | Focus | Duration | Status |
|-------|-------|----------|--------|
| **Phase 1** | Code Review & Analysis | 3-4 days | 📋 Planned |
| **Phase 2** | Local Mode Testing (3001/8001) | 2-3 days | 📋 Planned |
| **Phase 3** | Docker Mode Testing (3000/8000) | 2-3 days | 📋 Planned |
| **Phase 4** | Test Suite (70% coverage) | 5-7 days | 📋 Planned |
| **Phase 5** | Cloudflare Tunnel (HTTPS) | 2-3 days | 📋 Planned |
| **Phase 6** | Claude Agent SDK Integration | 5-7 days | 📋 Planned |
| **Phase 7** | Documentation & Production | 3-4 days | 📋 Planned |

**Feature Completion:**

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| **Phases 1-9A** | ✅ Complete | ~20% | Foundation, Chat, Proposals, Skills |
| **Phase 10** | ⚠️ 90% | <5% | Personas/Councils - needs verification |
| **Environment Setup** | ✅ Complete | - | Both Docker & Local modes configured |
| **Claude Agent SDK** | 📋 Ready | - | Auto-discovery capabilities identified |

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

## Docker Architecture

### Compose Files

```
docker-compose.yml        # Full production deployment
docker-compose.infra.yml  # Infrastructure only (postgres, chromadb)
docker-compose.dev.yml    # Dev mode with volume mounts for hot reload
```

### Port Allocation

| Service | Port | Notes |
|---------|------|-------|
| Frontend (Docker) | 3000 | Production-like |
| Frontend (Local) | 3001 | Hot reload |
| Backend (Docker) | 8000 | Production-like |
| Backend (Local) | 8001 | Hot reload |
| PostgreSQL | 5432 | Shared infrastructure |
| ChromaDB | 8002 | Shared infrastructure |

### Scripts

```bash
./scripts/infra.sh           # Start PostgreSQL + ChromaDB
./scripts/infra-stop.sh      # Stop all Docker services
./scripts/dev-local.sh       # Local dev (infra in Docker, app local)
./scripts/dev-docker.sh      # Docker dev (all in Docker with volumes)
./scripts/dev-docker-stop.sh # Stop Docker dev containers
```

### Critical Notes

- Vault mounted **read-write** (proposals need write access)
- USER_ID/GROUP_ID match host user (fixes permissions)
- ChromaDB on port 8002 (avoids conflict with local backend on 8001)
- Frontend uses `NEXT_PUBLIC_API_URL` env var for backend URL

---

## Phase 10: Council & Persona System (90% Complete)

**MAJOR DISCOVERY (Phase 0, 2026-01-02):**
- **52 Personas** exist in `Obsidian-Private/.claude/agents/` (Claude Agent SDK format)
- **34 Skills** exist in `Obsidian-Private/.claude/skills/` (including `call-council`)
- System architecture supports this via SDK auto-discovery (Phase 6)

**Concept:** Multi-persona consultations using existing persona library + call-council skill.

**Status:**
- ✅ Backend: query_persona_with_provider tool, subagent factory, API endpoints
- ✅ Personas: **52 personas in vault** (adam-grant, cal-newport, bessel-van-der-kolk, etc.)
- ✅ Skills: **34 custom skills in vault** (call-council for multi-persona orchestration)
- ⚠️ Integration: Needs SDK auto-discovery setup (Phase 6)
- ⚠️ Testing: Frontend/backend integration needs verification
- ❌ Tests: 0% coverage

**Sample Personas (52 total):**
- **Thought Leaders**: adam-grant, brene-brown, cal-newport
- **Health**: andrew-huberman, bessel-van-der-kolk, gabor-mate
- **Business**: alex-hormozi, dan-martell
- **Spiritual**: buddha
- **Utility**: calendar-assistant, document-classifier
- ... (44 more)

**Architecture:**
- Tool-based (LLM reads skills as instructions, not parsed data)
- SDK auto-discovery for personas/skills (Phase 6)
- call-council skill orchestrates multi-persona consultations

**See**: `docs/PERSONA-SKILLS-INVENTORY.md` for complete list

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

## 🤖 Claude Agent SDK Integration (Phase 6 - NEW!)

### Built-in Automatic Discovery ✅

The Claude Agent SDK has **native automatic skill discovery** - no manual scanning needed!

**Configuration** (Python):
```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Enable filesystem discovery
    allowed_tools=["Skill"],              # Enable Skills tool
    # Optional: specify project root (defaults to CWD)
    project_path=os.getenv("OBSIDIAN_VAULT_PATH")  # Points to Obsidian-Private
)
```

**What This Does:**
- ✅ Automatically discovers SKILL.md files from `.claude/skills/`
- ✅ Loads user skills: `~/.claude/skills/`
- ✅ Loads project skills: `<vault>/.claude/skills/`
- ✅ Project skills override user skills (same name)
- ✅ Skills discovered at startup (no manual scanning!)

### Current Vault Assets

**Obsidian-Private** already contains SDK-compliant assets:
```
Obsidian-Private/.claude/
├── skills/              # 35+ SKILL.md files (SDK-ready!)
│   ├── vision-setting/
│   ├── recovery-plan/
│   ├── goal-hierarchy/
│   └── [30+ more]
├── agents/              # 50+ agent definitions
│   ├── ray-dalio.md
│   ├── cal-newport.md
│   └── [48+ more]
├── commands/            # 20+ command definitions
│   ├── calendar.md
│   ├── tasks.md
│   └── [18+ more]
└── settings.local.json  # Permission settings
```

### Integration Plan

**Phase 6 Tasks:**
1. Configure SDK with `setting_sources=["user", "project"]`
2. Point `project_path` to Obsidian-Private
3. Verify auto-discovery on startup (should find 35+ skills)
4. Test skill matching and progressive loading
5. Create API endpoints to list/query discovered skills
6. Update frontend to show SDK-discovered skills

**Benefits:**
- Zero custom scanning code needed
- Official SDK support and updates
- Standard SKILL.md format
- Automatic reload on file changes (if configured)

**References:**
- [Agent SDK Skills Docs](https://platform.claude.com/docs/en/agent-sdk/skills)
- [Setting Sources Configuration](https://docs.claude.com/en/api/agent-sdk/overview)
- [Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)

---

## ☁️ Cloudflare Zero Trust Tunnel (Phase 5 - NEW!)

### Secure Remote Access

Production URLs (using **dare2b.nl** domain):
- **Production Frontend:** https://brain.dare2b.nl
- **Production API:** https://api.brain.dare2b.nl
- **Dev Frontend:** https://brain-dev.dare2b.nl
- **Dev API:** https://api-dev.dare2b.nl
- **Health Dashboard:** https://health.brain.dare2b.nl

### Setup Overview

```bash
# Install cloudflared
brew install cloudflare/cloudflare/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create sb-claude-tunnel

# Configure (~/.cloudflared/config.yml)
tunnel: <TUNNEL-ID>
credentials-file: ~/.cloudflared/<UUID>.json

ingress:
  - hostname: brain.dare2b.nl
    service: http://localhost:3000
  - hostname: api.brain.dare2b.nl
    service: http://localhost:8000
  - hostname: brain-dev.dare2b.nl
    service: http://localhost:3001
  - hostname: api-dev.dare2b.nl
    service: http://localhost:8001
  - service: http_status:404

# Route DNS
cloudflared tunnel route dns sb-claude-tunnel brain.dare2b.nl
# (repeat for other hostnames)

# Run as service
sudo cloudflared service install
sudo launchctl start com.cloudflare.cloudflared
```

### Authentication

**Cloudflare Access** (SSO):
- Identity providers: Google, GitHub, Email OTP
- Access policy: Allow tijlkoenderink@example.com
- Session duration: 24 hours
- Audit logging enabled

### Security Features

- ✅ No exposed ports/IP addresses
- ✅ Automatic HTTPS (TLS 1.3)
- ✅ DDoS protection (Cloudflare network)
- ✅ Bot mitigation
- ✅ Rate limiting (10 req/min per user)
- ✅ WAF (Web Application Firewall)
- ✅ Global CDN

### CORS Configuration

```python
# services/brain_runtime/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://brain.dare2b.nl",
        "https://brain-dev.dare2b.nl",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Frontend Configuration

```javascript
// apps/web/src/config.ts
export const API_URL =
  process.env.NODE_ENV === 'production'
    ? 'https://api.brain.dare2b.nl'
    : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
```

### Monitoring

- **Cloudflare Analytics:** Traffic, bandwidth, response codes
- **Tunnel Health:** `cloudflared tunnel info sb-claude-tunnel`
- **Logs:** `tail -f /var/log/cloudflared.log`
- **Alerts:** Email/Slack on tunnel disconnection, high error rates

**References:**
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [Zero Trust Access](https://developers.cloudflare.com/cloudflare-one/policies/access/)

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
| iCloud slow/hangs | ⚠️ Project IS in iCloud - May be slow. Force sync: `killall bird` |
| Vault read-only (Docker) | Mount as read-write (no `:ro` suffix) |
| Files owned by root (Docker) | Use USER_ID/GROUP_ID in .env (502/20) |
| Port conflict | Local: 3001/8001, Docker: 3000/8000 |
| Wrong backend in browser | Check NEXT_PUBLIC_API_URL matches your mode |
| ChromaDB connection fails | Ensure port 8002 (not 8001) |
| Skills not discovered | Verify `setting_sources=["user", "project"]` in SDK config |

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
