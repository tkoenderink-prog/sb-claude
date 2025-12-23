# Scenario 3: Hybrid MVP Implementation Plan
**Timeline:** 4 weeks + ongoing maintenance
**Goal:** Ship personal-use MVP early, achieve full test coverage, add Docker deployment
**Adjusted:** Skip accessibility (personal use), full 70% test coverage, Docker-first deployment

---

## OVERVIEW

**Strategy:** Staged deployment with continuous hardening
- Week 1: Fix blockers → Personal beta (you use it!)
- Week 2: Expand testing → Internal confidence
- Week 3: Full test coverage + Docker → Production-ready
- Week 4: Performance + polish → Solid MVP complete

**Key Adjustments from Standard Scenario 3:**
- ❌ No accessibility work (personal use, single user)
- ✅ Full 70% test coverage (not 50%)
- ✅ Docker-first deployment (not optional)
- ✅ Performance optimization included

---

## WEEK 1: CRITICAL PATH (Days 1-5)
**Goal:** Fix blockers, basic testing, deploy to personal beta

### Day 1: Python Environment + Linter (4 hours)

**Morning: Fix Python Clarity**
```bash
# 1. Document the uv run vs uv pip issue
# Create docs/PYTHON_ENVIRONMENT.md explaining:
# - uv run uses .venv (3.11.10) ✅
# - uv pip queries wrong environment (conda 3.12.4) ❌
# - Always use `uv run <command>`

# 2. Verify environment
uv run python --version  # Should be 3.11.10
uv run pytest --co -q    # Should collect tests without import errors

# 3. If import errors persist, recreate venv
rm -rf .venv
uv sync
uv run pytest --co -q
```

**Afternoon: Fix Linter Warnings**
```bash
# 1. Auto-fix what can be fixed
cd services/brain_runtime
uv run ruff check . --fix

# 2. Manual fixes
# - Remove unused import 'delete' from context_files.py:11
# - Remove unused import 'UUID' from personas.py:4
# - Fix boolean comparison in personas.py:64 (use 'is True')

# 3. Verify clean
uv run ruff check .  # Should be 0 errors

# 4. Fix frontend warning
# Edit apps/web/src/hooks/useChat.ts:295
# Add 'sessionTitle' to dependency array
```

**Deliverables:**
- [ ] PYTHON_ENVIRONMENT.md created
- [ ] All linter warnings fixed (Python + TypeScript)
- [ ] Tests collect without import errors
- [ ] Commit: "fix: resolve linter warnings and Python environment docs"

---

### Day 2: Essential Error Handling (6 hours)

**Backend Error Handling**

```python
# Priority files to add try/catch:

# 1. services/brain_runtime/api/chat.py:705
# Wrap database commit in try/except
try:
    await db.commit()
    logger.info(f"Session {session.id} committed")
except Exception as e:
    await db.rollback()
    logger.error(f"Failed to commit session: {e}")
    raise AppError(f"Failed to save chat session: {str(e)}")

# 2. services/brain_runtime/api/vault.py:220
# Log errors instead of silent failure
except Exception as e:
    logger.error(f"Semantic search failed: {e}", exc_info=True)
    return []

# 3. services/brain_runtime/api/vault.py:312
# Log timeout
except subprocess.TimeoutExpired as e:
    logger.warning(f"Vault search timed out after {timeout}s: {query}")
    return []
```

**Frontend Error Boundaries**

```typescript
// 1. Create apps/web/src/components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  level: 'app' | 'page' | 'component'
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error(`[${this.props.level}] Error caught:`, error, errorInfo)
    // TODO: Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <h2 className="text-red-900 font-semibold">Something went wrong</h2>
          <p className="text-red-700 text-sm mt-2">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded"
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

// 2. Wrap app in apps/web/src/app/layout.tsx
import { ErrorBoundary } from '@/components/ErrorBoundary'

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <ErrorBoundary level="app">
          <Providers>
            {children}
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  )
}

// 3. Wrap chat page in apps/web/src/app/chat/page.tsx
export default function ChatPage() {
  return (
    <ErrorBoundary level="page" fallback={<div>Chat unavailable</div>}>
      <ChatContainer />
    </ErrorBoundary>
  )
}
```

**Deliverables:**
- [ ] Try/catch added to 5 critical backend paths
- [ ] ErrorBoundary component created
- [ ] App, page, and component-level boundaries added
- [ ] Commit: "feat: add comprehensive error handling"

---

### Day 3: Phase 10 Verification (5 hours)

**Verify Chat Integration**

```bash
# 1. Check if personas are wired into chat
grep -n "create_all_persona_subagents" services/brain_runtime/api/chat.py

# If not found, add to api/chat.py around line 200:
from core.persona_subagents import create_all_persona_subagents

# In the chat endpoint, before creating SDK runtime:
persona_subagents = await create_all_persona_subagents(db)
subagents = {**default_subagents, **persona_subagents}

# 2. Check if tool is registered
grep -n "query_persona_with_provider" services/brain_runtime/core/tools/__init__.py

# If not found, add to core/tools/__init__.py:
from .persona_query import register_persona_query_tool
# And call in register_all_tools():
register_persona_query_tool(registry)

# 3. Verify database columns
psql -d second_brain -c "\d chat_sessions" | grep persona

# If missing, run migration:
psql -d second_brain -f services/brain_runtime/migrations/005_persona_council.sql
```

**Manual Testing**

```bash
# 1. Start servers
./scripts/dev.sh

# 2. Open http://localhost:3000/chat

# 3. Create new chat
# - Select "Socratic" as lead persona
# - Select council members: Contrarian, Pragmatist

# 4. Send message:
"Should I quit my job to start a startup? Invoke Decision Council."

# 5. Verify SSE events:
# - Should see 3 tool_call events (one per persona)
# - Should see 3 tool_result events
# - Should see council synthesis

# 6. Check database:
psql -d second_brain -c "SELECT lead_persona_id, council_member_ids FROM chat_sessions ORDER BY created_at DESC LIMIT 1;"
```

**Deliverables:**
- [ ] Personas wired into chat endpoint
- [ ] Tool registered in registry
- [ ] Database columns verified
- [ ] Manual test passed
- [ ] Commit: "feat: complete Phase 10 integration"

---

### Day 4: Core Testing Infrastructure (6 hours)

**Backend Testing Setup**

```bash
# 1. Create pytest configuration
cat > services/brain_runtime/pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
EOF

# 2. Create test fixtures
mkdir -p services/brain_runtime/tests
cat > services/brain_runtime/tests/conftest.py << 'EOF'
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.database import Base

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        "postgresql+asyncpg://tijlkoenderink@localhost:5432/second_brain_test",
        echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine):
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()
EOF

# 3. Create test database
psql -c "CREATE DATABASE second_brain_test;" || echo "Test DB already exists"
psql -d second_brain_test -f scripts/init_db.sql
```

**Write Critical Backend Tests**

```python
# tests/test_persona_query_tool.py
import pytest
from core.tools.persona_query import query_persona_with_provider

@pytest.mark.asyncio
async def test_query_persona_basic(db_session):
    """Test basic persona query"""
    result = await query_persona_with_provider(
        db=db_session,
        persona_name="Socratic",
        provider="anthropic",
        user_question="What is the meaning of life?"
    )

    assert result is not None
    assert len(result) > 0
    assert "?" in result  # Socratic asks questions

@pytest.mark.asyncio
async def test_query_persona_with_skills(db_session):
    """Test persona uses persona-specific skills"""
    result = await query_persona_with_provider(
        db=db_session,
        persona_name="Pragmatist",
        provider="anthropic",
        user_question="How should I prioritize my tasks?"
    )

    assert "80/20" in result.lower() or "pareto" in result.lower()

# tests/test_chat_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_chat_endpoint_basic():
    """Test basic chat endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "mode": "tools",
                "provider": "anthropic"
            }
        )
        assert response.status_code == 200

# tests/test_error_handling.py
import pytest
from core.errors import AppError, ToolError

@pytest.mark.asyncio
async def test_database_rollback_on_error(db_session):
    """Verify database rolls back on errors"""
    from models.db_models import ChatSessionDB

    session = ChatSessionDB(title="Test")
    db_session.add(session)

    with pytest.raises(Exception):
        # Simulate error
        raise AppError("Test error")

    await db_session.rollback()
    # Session should not be committed
```

**Frontend Testing Setup**

```bash
# 1. Install Vitest + React Testing Library
cd apps/web
pnpm add -D vitest @testing-library/react @testing-library/jest-dom @vitejs/plugin-react jsdom

# 2. Create vitest config
cat > vitest.config.ts << 'EOF'
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
EOF

# 3. Create test setup
mkdir -p apps/web/src/test
cat > apps/web/src/test/setup.ts << 'EOF'
import '@testing-library/jest-dom'
EOF
```

**Write Critical Frontend Tests**

```typescript
// src/hooks/__tests__/useChat.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useChat } from '../useChat'

const createWrapper = () => {
  const queryClient = new QueryClient()
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useChat', () => {
  it('initializes with empty messages', () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    })

    expect(result.current.messages).toEqual([])
    expect(result.current.isStreaming).toBe(false)
  })

  it('adds message when sending', async () => {
    const { result } = renderHook(() => useChat(), {
      wrapper: createWrapper(),
    })

    await result.current.sendMessage('Hello')

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThan(0)
    })
  })
})

// src/components/chat/__tests__/MessageBubble.test.tsx
import { render, screen } from '@testing-library/react'
import MessageBubble from '../MessageBubble'

describe('MessageBubble', () => {
  it('renders user message', () => {
    render(
      <MessageBubble
        message={{ role: 'user', content: 'Hello' }}
        isStreaming={false}
      />
    )

    expect(screen.getByText('Hello')).toBeInTheDocument()
  })

  it('renders assistant message', () => {
    render(
      <MessageBubble
        message={{ role: 'assistant', content: 'Hi there!' }}
        isStreaming={false}
      />
    )

    expect(screen.getByText('Hi there!')).toBeInTheDocument()
  })
})
```

**Run Tests**

```bash
# Backend
cd services/brain_runtime
uv run pytest -v

# Frontend
cd apps/web
pnpm test

# Target: 10-15% coverage
# Critical paths working
```

**Deliverables:**
- [ ] Pytest configured with fixtures
- [ ] Test database created
- [ ] 5-10 backend tests written
- [ ] Vitest configured
- [ ] 3-5 frontend tests written
- [ ] All tests passing
- [ ] Commit: "test: add core testing infrastructure"

---

### Day 5: Security + Deploy to Beta (5 hours)

**Add Rate Limiting**

```python
# 1. Install slowapi
# Add to pyproject.toml dependencies:
# slowapi>=0.1.9

# 2. Configure in main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Apply to endpoints
from slowapi import Limiter
from fastapi import Request

@app.post("/chat")
@limiter.limit("20/minute")  # 20 requests per minute
async def chat(request: Request, ...):
    ...

@app.post("/vault/search")
@limiter.limit("100/minute")
async def vault_search(request: Request, ...):
    ...
```

**Restrict CORS**

```python
# In core/config.py, change:
cors_origins: list[str] = ["http://localhost:3000"]  # Remove wildcard

# In main.py:
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Specific methods
    allow_headers=["Content-Type", "Authorization"],  # Specific headers
)
```

**Mask API Keys in UI**

```typescript
// apps/web/src/app/settings/page.tsx
function maskApiKey(key: string): string {
  if (key.length <= 8) return key
  return `${key.slice(0, 4)}${'*'.repeat(key.length - 8)}${key.slice(-4)}`
}

// In render:
<span className="font-mono">{maskApiKey(apiKey.key)}</span>
```

**Git Setup for Application**

```bash
# 1. Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/

# Node
node_modules/
.next/
out/
.turbo/

# Environment & Secrets
.env
.env.local
.env.*.local
data/secrets/
*.pem
*.key

# Database
*.db
*.sql
data/postgres/

# Logs
*.log
data/logs/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Build artifacts
dist/
build/
*.whl

# Test coverage
.coverage
htmlcov/
.pytest_cache/

# ChromaDB
chroma_data/
EOF

# 2. Initialize git
git init
git add .
git commit -m "Initial commit: Second Brain v0.9"

# 3. Create GitHub repo (via gh CLI or web)
gh repo create second-brain-app --private --source=. --remote=origin

# 4. Push to GitHub
git push -u origin main

# 5. Add branch protection (optional)
gh repo edit --enable-auto-merge=false \
  --delete-branch-on-merge

# 6. Create development branch
git checkout -b development
git push -u origin development

echo "✅ Git setup complete! Repository: $(gh repo view --json url -q .url)"
```

**Beta Deployment Checklist**

```bash
# 1. Update environment variables
cp .env .env.backup
# Review and update any production-specific values

# 2. Database backup
pg_dump second_brain > backups/second_brain_$(date +%Y%m%d).sql

# 3. Start services
./scripts/dev.sh

# 4. Smoke test
curl http://localhost:8000/health
open http://localhost:3000

# 5. Manual testing
# - Create new chat
# - Test persona selection
# - Invoke Decision Council
# - Test proposal workflow
# - Test skill attachment
# - Test vault search

# 6. Monitor logs
tail -f data/logs/*.log
```

**Deliverables:**
- [ ] Rate limiting added to critical endpoints
- [ ] CORS restricted to localhost
- [ ] API keys masked in UI
- [ ] Git repository initialized and pushed to GitHub
- [ ] .gitignore configured for secrets/data
- [ ] Beta deployment smoke tested
- [ ] Commit: "feat: security hardening + git setup for beta"

**🎉 END OF WEEK 1: BETA DEPLOYED + VERSION CONTROLLED**

**Status:** You can now use the system with:
- ✅ Phase 10 personas working
- ✅ Basic error handling
- ✅ Core tests passing
- ✅ Security essentials
- ~15% test coverage

---

## WEEK 2: MONITORING + GIT + TESTING (Days 6-10)
**Goal:** Monitor usage, add vault git management, expand test coverage to 40%

### Day 6: Usage Monitoring + Bug Fixes (6 hours)

**Add Structured Logging**

```python
# core/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(handlers=[handler], level=logging.INFO)

# In main.py:
from core.logging_config import setup_logging
setup_logging()
```

**Monitor Real Usage**

```bash
# 1. Create monitoring dashboard (simple script)
cat > scripts/monitor.sh << 'EOF'
#!/bin/bash
echo "=== Chat Sessions (Last 24h) ==="
psql -d second_brain -c "
  SELECT COUNT(*), AVG(EXTRACT(EPOCH FROM (updated_at - created_at))) as avg_duration_seconds
  FROM chat_sessions
  WHERE created_at > NOW() - INTERVAL '24 hours';
"

echo ""
echo "=== Error Rate (Last Hour) ==="
grep -c "ERROR" data/logs/*.log | tail -1

echo ""
echo "=== Most Used Skills ==="
psql -d second_brain -c "
  SELECT skill_name, COUNT(*) as usage_count
  FROM skill_usage
  WHERE used_at > NOW() - INTERVAL '24 hours'
  GROUP BY skill_name
  ORDER BY usage_count DESC
  LIMIT 10;
"

echo ""
echo "=== Council Invocations ==="
psql -d second_brain -c "
  SELECT COUNT(*)
  FROM user_skills
  WHERE category = 'council'
  AND last_used_at > NOW() - INTERVAL '24 hours';
"
EOF

chmod +x scripts/monitor.sh

# 2. Run daily
./scripts/monitor.sh
```

**Bug Triage Process**

```bash
# 1. Check error logs
grep "ERROR\|CRITICAL" data/logs/*.log | tail -20

# 2. Check failed tests
uv run pytest -v --tb=short | grep FAILED

# 3. Reproduce bugs manually
# 4. Write failing test
# 5. Fix bug
# 6. Verify test passes
```

**Deliverables:**
- [ ] Structured logging implemented
- [ ] Monitoring dashboard created
- [ ] Any critical bugs fixed
- [ ] Tests added for bug fixes
- [ ] Commit: "feat: add monitoring and fix critical bugs"

---

### Day 7: Health Dashboard + Vault Git Management (9 hours)

**Goal:** UI monitoring + vault git integration

**Morning: Health Dashboard UI (4 hours)**

```typescript
// apps/web/src/app/health/page.tsx
import { VaultGitCard } from '@/components/health/VaultGitCard'
import { SystemStatsCard } from '@/components/health/SystemStatsCard'
import { RecentActivityCard } from '@/components/health/RecentActivityCard'

export default function HealthDashboard() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6">
      <VaultGitCard />
      <SystemStatsCard />
      <RecentActivityCard />
    </div>
  )
}

// components/health/SystemStatsCard.tsx
export function SystemStatsCard() {
  const { data: stats } = useQuery(['system-stats'], fetchSystemStats)

  return (
    <Card>
      <CardHeader>📊 System Stats (24h)</CardHeader>
      <CardContent>
        <div className="space-y-2">
          <StatRow label="Chat Sessions" value={stats?.sessions || 0} />
          <StatRow label="Proposals Created" value={stats?.proposals || 0} />
          <StatRow label="Skills Used" value={stats?.skills_used || 0} />
          <StatRow label="Council Invocations" value={stats?.councils || 0} />
        </div>
      </CardContent>
    </Card>
  )
}
```

**Afternoon: Vault Git Service (3 hours)**

```python
# services/brain_runtime/core/git_service.py
import git
from pathlib import Path
from typing import Optional
from datetime import datetime

class GitStatus:
    """Git status for vault"""
    last_commit: Optional[dict]
    uncommitted_files: list[str]
    is_dirty: bool
    remote_ahead: int
    remote_behind: int
    is_git_repo: bool

class VaultGitService:
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        try:
            self.repo = git.Repo(vault_path)
            self.is_git_repo = True
        except git.InvalidGitRepositoryError:
            self.is_git_repo = False
            self.repo = None

    async def get_status(self) -> GitStatus:
        """Get current git status"""
        if not self.is_git_repo:
            return GitStatus(is_git_repo=False)

        # Get last commit
        last_commit = None
        if self.repo.head.is_valid():
            commit = self.repo.head.commit
            last_commit = {
                "message": commit.message.strip(),
                "author": commit.author.name,
                "date": commit.committed_datetime.isoformat(),
                "sha": commit.hexsha[:7]
            }

        # Get uncommitted files
        uncommitted = [
            item.a_path for item in self.repo.index.diff(None)
        ] + self.repo.untracked_files

        # Check remote status
        remote_ahead = 0
        remote_behind = 0
        try:
            remote_ahead = len(list(self.repo.iter_commits('origin/main..HEAD')))
            remote_behind = len(list(self.repo.iter_commits('HEAD..origin/main')))
        except:
            pass  # No remote or not fetched

        return GitStatus(
            last_commit=last_commit,
            uncommitted_files=uncommitted,
            is_dirty=self.repo.is_dirty(untracked_files=True),
            remote_ahead=remote_ahead,
            remote_behind=remote_behind,
            is_git_repo=True
        )

    async def commit_changes(
        self,
        message: str,
        files: Optional[list[str]] = None
    ):
        """Commit specific files or all changes"""
        if not self.is_git_repo:
            raise ValueError("Not a git repository")

        if files:
            self.repo.index.add(files)
        else:
            self.repo.git.add(A=True)

        self.repo.index.commit(message)

    async def sync(self) -> dict:
        """Pull, commit, push"""
        if not self.is_git_repo:
            raise ValueError("Not a git repository")

        try:
            # Pull first
            self.repo.git.pull()

            # Commit if dirty
            if self.repo.is_dirty(untracked_files=True):
                await self.commit_changes("Auto-sync from Second Brain")

            # Push
            self.repo.git.push()

            return {"success": True, "message": "Synced successfully"}
        except git.GitCommandError as e:
            return {"success": False, "error": str(e)}

    async def get_diff(self, file_path: Optional[str] = None) -> str:
        """Get diff for file or all changes"""
        if not self.is_git_repo:
            return ""

        if file_path:
            return self.repo.git.diff(file_path)
        else:
            return self.repo.git.diff()

# Add to pyproject.toml dependencies
# gitpython>=3.1.40
```

**Evening: API Endpoints + Frontend Integration (2 hours)**

```python
# api/vault_git.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.git_service import VaultGitService, GitStatus
from core.config import get_settings

router = APIRouter(prefix="/vault/git", tags=["vault-git"])

@router.get("/status")
async def get_vault_git_status() -> GitStatus:
    """Get current git status of vault"""
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    return await git_service.get_status()

@router.post("/sync")
async def sync_vault_git() -> dict:
    """Pull, commit all changes, push"""
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    return await git_service.sync()

@router.get("/diff")
async def get_vault_diff(file_path: Optional[str] = None) -> dict:
    """Get diff for file or entire vault"""
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    diff = await git_service.get_diff(file_path)
    return {"diff": diff}

# Register in main.py
app.include_router(vault_git.router)
```

```typescript
// components/health/VaultGitCard.tsx
import { useQuery, useMutation } from '@tanstack/react-query'
import { Card, CardHeader, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function VaultGitCard() {
  const { data: gitStatus, refetch } = useQuery(
    ['vault-git-status'],
    () => fetch('/api/vault/git/status').then(r => r.json())
  )

  const syncMutation = useMutation(
    () => fetch('/api/vault/git/sync', { method: 'POST' }).then(r => r.json()),
    { onSuccess: () => refetch() }
  )

  if (!gitStatus?.is_git_repo) {
    return (
      <Card>
        <CardHeader>📦 Vault Git Status</CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            Vault is not a git repository
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>📦 Vault Git Status</CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Last commit */}
          {gitStatus.last_commit && (
            <div>
              <div className="text-sm font-medium">Last Commit:</div>
              <div className="text-xs text-muted-foreground">
                {gitStatus.last_commit.message}
              </div>
              <div className="text-xs text-muted-foreground">
                by {gitStatus.last_commit.author} • {
                  new Date(gitStatus.last_commit.date).toRelativeTime()
                }
              </div>
            </div>
          )}

          {/* Uncommitted changes */}
          {gitStatus.is_dirty && (
            <div>
              <div className="text-sm font-medium text-yellow-600">
                Uncommitted: {gitStatus.uncommitted_files.length} files
              </div>
              <div className="text-xs space-y-1 mt-1">
                {gitStatus.uncommitted_files.slice(0, 3).map(file => (
                  <div key={file} className="truncate">{file}</div>
                ))}
                {gitStatus.uncommitted_files.length > 3 && (
                  <div>+{gitStatus.uncommitted_files.length - 3} more...</div>
                )}
              </div>
            </div>
          )}

          {/* Remote status */}
          <div className="flex items-center gap-2 text-sm">
            <span>Remote:</span>
            {gitStatus.remote_ahead > 0 && (
              <span className="text-blue-600">↑ {gitStatus.remote_ahead} ahead</span>
            )}
            {gitStatus.remote_behind > 0 && (
              <span className="text-orange-600">↓ {gitStatus.remote_behind} behind</span>
            )}
            {gitStatus.remote_ahead === 0 && gitStatus.remote_behind === 0 && (
              <span className="text-green-600">✓ In sync</span>
            )}
          </div>

          {/* Actions */}
          <Button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isLoading}
            size="sm"
          >
            {syncMutation.isLoading ? 'Syncing...' : 'Commit & Push'}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
```

**Settings Integration**

```sql
-- Add to migrations (or update user_settings table)
ALTER TABLE user_settings ADD COLUMN git_settings JSONB DEFAULT '{
  "auto_commit_on_edit": true,
  "auto_push": false,
  "commit_message_template": "[Second Brain] {action}"
}'::jsonb;
```

```typescript
// apps/web/src/app/settings/page.tsx
// Add Git Settings section
export function GitSettingsPanel() {
  const { data: settings, mutate } = useSettings()

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Vault Git Settings</h3>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={settings?.git_settings?.auto_commit_on_edit}
          onChange={(e) => mutate({
            git_settings: {
              ...settings.git_settings,
              auto_commit_on_edit: e.target.checked
            }
          })}
        />
        <span className="text-sm">Auto-commit on proposal apply</span>
      </label>

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={settings?.git_settings?.auto_push}
          onChange={(e) => mutate({
            git_settings: {
              ...settings.git_settings,
              auto_push: e.target.checked
            }
          })}
        />
        <span className="text-sm">Auto-push after commit</span>
      </label>
    </div>
  )
}
```

**Proposal Integration (Auto-commit)**

```python
# core/proposal_service.py
async def apply_proposal_with_git(
    proposal: Proposal,
    settings: dict
):
    """Apply proposal with git commits before/after"""
    from core.git_service import VaultGitService

    git_settings = settings.get("git_settings", {})
    if not git_settings.get("auto_commit_on_edit"):
        # Just apply normally
        return await apply_proposal(proposal)

    git_service = VaultGitService(vault_path)

    # Pre-edit commit
    if git_service.is_git_repo:
        try:
            await git_service.commit_changes(
                f"Pre-edit: {proposal.title}",
                files=proposal.affected_files
            )
        except Exception as e:
            logger.warning(f"Pre-edit commit failed: {e}")

    # Apply changes
    result = await apply_proposal(proposal)

    # Post-edit commit
    if git_service.is_git_repo:
        try:
            await git_service.commit_changes(
                f"[Second Brain] Applied: {proposal.title}",
                files=proposal.affected_files
            )

            # Auto-push if enabled
            if git_settings.get("auto_push"):
                await git_service.sync()
        except Exception as e:
            logger.warning(f"Post-edit commit failed: {e}")

    return result
```

**Deliverables:**
- [ ] Health dashboard UI created
- [ ] VaultGitService implemented
- [ ] Git status API endpoints working
- [ ] VaultGitCard component displays status
- [ ] Git settings in UI
- [ ] Auto-commit on proposal apply (with setting)
- [ ] Commit: "feat: add health dashboard and vault git management"

---

### Day 8-9: Expand Backend Test Coverage (12 hours)

**Goal:** 40% backend coverage

**API Endpoint Tests**

```python
# tests/test_api_vault.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_vault_read():
    """Test vault file reading"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/vault/read",
            json={"file_path": "README.md"}
        )
        assert response.status_code == 200
        assert "content" in response.json()

@pytest.mark.asyncio
async def test_vault_search():
    """Test vault search"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/vault/search",
            json={"query": "test", "limit": 10}
        )
        assert response.status_code == 200

# tests/test_api_proposals.py
@pytest.mark.asyncio
async def test_create_proposal(db_session):
    """Test proposal creation"""
    from core.proposal_service import ProposalService

    service = ProposalService(db_session)
    proposal = await service.create_proposal(
        session_id=uuid.uuid4(),
        file_path="test.md",
        old_content="old",
        new_content="new",
        explanation="Test change"
    )

    assert proposal.id is not None
    assert proposal.status == "pending"

# tests/test_api_personas.py
@pytest.mark.asyncio
async def test_get_personas():
    """Test personas endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/personas")
        assert response.status_code == 200
        personas = response.json()
        assert len(personas) == 5  # Default personas
```

**Service Layer Tests**

```python
# tests/test_session_service.py
import pytest
from core.session_service import SessionService

@pytest.mark.asyncio
async def test_create_session(db_session):
    """Test session creation"""
    service = SessionService(db_session)
    session = await service.create_session(
        mode_id=uuid.uuid4(),
        title="Test Chat"
    )

    assert session.id is not None
    assert session.title == "Test Chat"

@pytest.mark.asyncio
async def test_load_messages(db_session):
    """Test message loading"""
    service = SessionService(db_session)
    messages = await service.load_messages(session_id=uuid.uuid4())
    assert isinstance(messages, list)
```

**Tool Tests**

```python
# tests/test_tools.py
import pytest
from core.tools.vault_tools import read_vault_file, search_vault

@pytest.mark.asyncio
async def test_read_vault_file():
    """Test vault file reading"""
    content = await read_vault_file("README.md")
    assert content is not None
    assert len(content) > 0

@pytest.mark.asyncio
async def test_search_vault():
    """Test vault search"""
    results = await search_vault("test", limit=5)
    assert isinstance(results, list)
```

**Run Coverage Report**

```bash
# Install coverage
uv add --dev pytest-cov

# Run with coverage
uv run pytest --cov=. --cov-report=html --cov-report=term

# View report
open htmlcov/index.html

# Target: 40% coverage
```

**Deliverables:**
- [ ] 20+ API endpoint tests
- [ ] 10+ service layer tests
- [ ] 10+ tool tests
- [ ] Coverage report generated
- [ ] 40% coverage achieved
- [ ] Commit: "test: expand backend test coverage to 40%"

---

### Day 10: Expand Frontend Test Coverage (6 hours)

**Goal:** 30% frontend coverage

**Hook Tests**

```typescript
// src/hooks/__tests__/useProposals.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { useProposals } from '../useProposals'

describe('useProposals', () => {
  it('loads pending proposals', async () => {
    const { result } = renderHook(() => useProposals('pending'), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.proposals).toBeDefined()
    })
  })

  it('accepts proposal', async () => {
    const { result } = renderHook(() => useProposals('pending'), {
      wrapper: createWrapper(),
    })

    await result.current.acceptProposal('proposal-id')

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true)
    })
  })
})

// src/hooks/__tests__/usePersonas.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { usePersonas } from '../usePersonas'

describe('usePersonas', () => {
  it('loads personas', async () => {
    const { result } = renderHook(() => usePersonas(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.personas).toHaveLength(5)
    })
  })
})
```

**Component Tests**

```typescript
// src/components/chat/__tests__/ChatContainer.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import ChatContainer from '../ChatContainer'

describe('ChatContainer', () => {
  it('renders message input', () => {
    render(<ChatContainer />)
    expect(screen.getByPlaceholderText(/message/i)).toBeInTheDocument()
  })

  it('sends message on submit', async () => {
    render(<ChatContainer />)
    const input = screen.getByPlaceholderText(/message/i)
    const button = screen.getByRole('button', { name: /send/i })

    fireEvent.change(input, { target: { value: 'Hello' } })
    fireEvent.click(button)

    await waitFor(() => {
      expect(screen.getByText('Hello')).toBeInTheDocument()
    })
  })
})

// src/components/proposal/__tests__/ProposalCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import ProposalCard from '../ProposalCard'

describe('ProposalCard', () => {
  const mockProposal = {
    id: '123',
    file_path: 'test.md',
    old_content: 'old',
    new_content: 'new',
    status: 'pending',
  }

  it('renders proposal details', () => {
    render(<ProposalCard proposal={mockProposal} />)
    expect(screen.getByText('test.md')).toBeInTheDocument()
  })

  it('accepts proposal on click', async () => {
    const onAccept = vi.fn()
    render(<ProposalCard proposal={mockProposal} onAccept={onAccept} />)

    const acceptButton = screen.getByText(/accept/i)
    fireEvent.click(acceptButton)

    expect(onAccept).toHaveBeenCalledWith('123')
  })
})
```

**SSE Parsing Tests**

```typescript
// src/lib/__tests__/chat-api.test.ts
import { parseSSEEvent } from '../chat-api'

describe('SSE Parsing', () => {
  it('parses text event', () => {
    const event = parseSSEEvent('data: {"type":"text","data":{"text":"Hello"}}')
    expect(event.type).toBe('text')
    expect(event.data.text).toBe('Hello')
  })

  it('parses tool call event', () => {
    const event = parseSSEEvent('data: {"type":"tool_call","data":{"name":"search","args":{}}}')
    expect(event.type).toBe('tool_call')
    expect(event.data.name).toBe('search')
  })

  it('parses council event', () => {
    const event = parseSSEEvent('data: {"type":"council","data":{"members":[]}}')
    expect(event.type).toBe('council')
  })
})
```

**Run Coverage**

```bash
cd apps/web

# Run tests with coverage
pnpm test -- --coverage

# View report
open coverage/index.html

# Target: 30% coverage
```

**Deliverables:**
- [ ] 10+ hook tests
- [ ] 15+ component tests
- [ ] SSE parsing tests
- [ ] Coverage report
- [ ] 30% frontend coverage
- [ ] Commit: "test: expand frontend test coverage to 30%"

**🎉 END OF WEEK 2: SOLID TESTING FOUNDATION**

**Status:**
- ✅ ~40% backend coverage
- ✅ ~30% frontend coverage
- ✅ Monitoring in place
- ✅ Critical bugs fixed
- ✅ Personal usage ongoing

---

## WEEK 3: FULL COVERAGE + DOCKER (Days 11-15)
**Goal:** 70% test coverage, Docker deployment ready

### Day 11-12: Backend Test Coverage to 70% (12 hours)

**Integration Tests**

```python
# tests/integration/test_chat_flow.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_chat_flow():
    """Test complete chat flow from start to finish"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Create session
        create_response = await client.post(
            "/sessions",
            json={"mode": "tools", "title": "Test Chat"}
        )
        session_id = create_response.json()["id"]

        # 2. Send message
        chat_response = await client.post(
            "/chat",
            json={
                "session_id": session_id,
                "messages": [{"role": "user", "content": "What is 2+2?"}],
                "mode": "tools"
            }
        )
        assert chat_response.status_code == 200

        # 3. Get messages
        messages_response = await client.get(f"/sessions/{session_id}/messages")
        messages = messages_response.json()
        assert len(messages) >= 2  # User message + assistant response

@pytest.mark.integration
@pytest.mark.asyncio
async def test_council_invocation():
    """Test Decision Council end-to-end"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Should I quit my job? Invoke Decision Council."}
                ],
                "mode": "agent",
                "provider": "anthropic"
            }
        )

        # Verify council was invoked
        # Check for 3 persona queries in tool calls
        # Verify synthesis in response

@pytest.mark.integration
@pytest.mark.asyncio
async def test_proposal_workflow():
    """Test proposal creation and acceptance"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Create proposal
        create_response = await client.post(
            "/proposals",
            json={
                "file_path": "test.md",
                "old_content": "old",
                "new_content": "new",
                "explanation": "Test change"
            }
        )
        proposal_id = create_response.json()["id"]

        # 2. Get pending proposals
        list_response = await client.get("/proposals?status=pending")
        proposals = list_response.json()
        assert any(p["id"] == proposal_id for p in proposals)

        # 3. Accept proposal
        accept_response = await client.post(f"/proposals/{proposal_id}/accept")
        assert accept_response.status_code == 200

        # 4. Verify file written
        # Check vault file system
```

**Edge Case Tests**

```python
# tests/test_edge_cases.py
import pytest

@pytest.mark.asyncio
async def test_empty_message():
    """Test handling of empty messages"""
    # Should return validation error

@pytest.mark.asyncio
async def test_missing_session():
    """Test querying non-existent session"""
    # Should return 404

@pytest.mark.asyncio
async def test_concurrent_tool_calls():
    """Test multiple tools called simultaneously"""
    # Should handle without race conditions

@pytest.mark.asyncio
async def test_large_file_read():
    """Test reading very large vault file"""
    # Should handle without memory issues

@pytest.mark.asyncio
async def test_invalid_persona():
    """Test querying non-existent persona"""
    # Should return error
```

**Run Full Test Suite**

```bash
# Run all tests with markers
uv run pytest -v --cov=. --cov-report=html --cov-report=term -m "not slow"

# Run slow tests separately
uv run pytest -v -m slow

# Check coverage
uv run pytest --cov=. --cov-report=term | grep TOTAL

# Target: 70%+ coverage
```

**Deliverables:**
- [ ] 10+ integration tests
- [ ] 15+ edge case tests
- [ ] All tests passing
- [ ] 70% backend coverage
- [ ] Commit: "test: achieve 70% backend coverage"

---

### Day 13-14: Frontend Coverage to 70% + E2E (12 hours)

**Complete Hook Coverage**

```typescript
// Test all remaining hooks
// - useCommands
// - useCouncils
// - useModes
// - useProviders
// - useClientDate

// Example: src/hooks/__tests__/useCouncils.test.ts
describe('useCouncils', () => {
  it('loads council skills', async () => {
    const { result } = renderHook(() => useCouncils())
    await waitFor(() => {
      expect(result.current.councils).toHaveLength(3)
    })
  })
})
```

**Complete Component Coverage**

```typescript
// Test all chat components
// - ToolCallCard
// - ToolResultCard
// - SubagentCard
// - CouncilResponse
// - ContextFileSelector
// - etc.

// Example: src/components/chat/__tests__/CouncilResponse.test.tsx
describe('CouncilResponse', () => {
  it('renders all council members', () => {
    const councilData = {
      members: [
        { name: 'Socratic', icon: '🏛️', response: 'Questions...' },
        { name: 'Contrarian', icon: '😈', response: 'Critique...' },
      ],
      synthesis: 'Combined insight...'
    }

    render(<CouncilResponse data={councilData} />)
    expect(screen.getByText('Socratic')).toBeInTheDocument()
    expect(screen.getByText('Contrarian')).toBeInTheDocument()
  })
})
```

**E2E Tests (Playwright)**

```typescript
// tests/e2e/phase10-councils.spec.ts
import { test, expect } from '@playwright/test'

test('invoke Decision Council', async ({ page }) => {
  await page.goto('http://localhost:3000/chat')

  // Create new chat with Socratic persona
  await page.click('[data-testid="new-chat"]')
  await page.click('[data-testid="persona-socratic"]')
  await page.click('[data-testid="confirm"]')

  // Send message
  await page.fill('[data-testid="message-input"]', 'Should I quit my job? Invoke Decision Council.')
  await page.click('[data-testid="send-button"]')

  // Wait for council response
  await page.waitForSelector('[data-testid="council-response"]', { timeout: 30000 })

  // Verify 3 personas responded
  await expect(page.locator('[data-testid="council-member"]')).toHaveCount(3)

  // Verify synthesis
  await expect(page.locator('[data-testid="council-synthesis"]')).toBeVisible()
})

test('persona skills are scoped', async ({ page }) => {
  await page.goto('http://localhost:3000/chat')

  // Select Pragmatist
  await page.click('[data-testid="new-chat"]')
  await page.click('[data-testid="persona-pragmatist"]')
  await page.click('[data-testid="confirm"]')

  // Open skills panel
  await page.click('[data-testid="skills-panel"]')

  // Verify only Pragmatist + universal skills shown
  const skills = await page.locator('[data-testid="skill-item"]').allTextContents()
  expect(skills).toContain('80/20 Analysis')
  expect(skills).not.toContain('Socratic Questioning')
})
```

**Run All Frontend Tests**

```bash
cd apps/web

# Unit + component tests
pnpm test -- --coverage

# E2E tests
pnpm e2e

# Check coverage
cat coverage/coverage-summary.json | jq '.total.lines.pct'

# Target: 70%+ coverage
```

**Deliverables:**
- [ ] All hooks tested
- [ ] All components tested
- [ ] 5+ new E2E tests
- [ ] 70% frontend coverage
- [ ] Commit: "test: achieve 70% frontend coverage"

---

### Day 15: Docker Implementation (6 hours)

**Create Dockerfiles**

```dockerfile
# services/brain_runtime/Dockerfile
FROM python:3.11-slim

# Create non-root user matching host UID/GID (fixes file permissions)
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} app && \
    useradd -u ${USER_ID} -g app -m -s /bin/bash app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    ripgrep \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (as root, then switch user)
RUN pip install uv

# Copy dependency files
COPY --chown=app:app pyproject.toml .
COPY --chown=app:app uv.lock .

# Switch to non-root user
USER app

# Install dependencies as app user
RUN uv sync --frozen

# Copy application code
COPY --chown=app:app . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application as non-root user
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```dockerfile
# apps/web/Dockerfile
FROM node:20-alpine AS base

# Install pnpm
RUN npm install -g pnpm

FROM base AS dependencies
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

FROM base AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY . .
RUN pnpm build

FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=build /app/public ./public
COPY --from=build --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

**Create docker-compose.yml**

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: second-brain-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-secondbrain}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
      POSTGRES_DB: ${POSTGRES_DB:-second_brain}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./services/brain_runtime/migrations:/docker-entrypoint-initdb.d/migrations
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-secondbrain}"]
      interval: 10s
      timeout: 5s
      retries: 5

  chromadb:
    image: chromadb/chroma:latest
    container_name: second-brain-chroma
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8000"
    environment:
      IS_PERSISTENT: TRUE
      ANONYMIZED_TELEMETRY: FALSE

  backend:
    build:
      context: ./services/brain_runtime
      dockerfile: Dockerfile
      args:
        USER_ID: ${USER_ID:-1000}
        GROUP_ID: ${GROUP_ID:-1000}
    container_name: second-brain-backend
    depends_on:
      postgres:
        condition: service_healthy
      chromadb:
        condition: service_started
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-secondbrain}:${POSTGRES_PASSWORD:-changeme}@postgres:5432/${POSTGRES_DB:-second_brain}
      CHROMA_HOST: chromadb
      CHROMA_PORT: 8000
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}
      OBSIDIAN_VAULT_PATH: /vault
      CALENDAR_WORK_URL: ${CALENDAR_WORK_URL:-}
      CALENDAR_PRIVATE_URL: ${CALENDAR_PRIVATE_URL:-}
      API_KEY_ENCRYPTION_KEY: ${API_KEY_ENCRYPTION_KEY}
    volumes:
      - "${OBSIDIAN_VAULT_PATH}:/vault"  # Read-write (proposals need write access!)
      - backend_data:/app/data
    ports:
      - "8000:8000"
    restart: unless-stopped

  frontend:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    container_name: second-brain-frontend
    depends_on:
      - backend
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
    ports:
      - "3000:3000"
    restart: unless-stopped

volumes:
  postgres_data:
  chroma_data:
  backend_data:

networks:
  default:
    name: second-brain-network
```

**Create .env.docker**

```bash
# .env.docker
# Copy to .env before running docker-compose

# Database
POSTGRES_USER=secondbrain
POSTGRES_PASSWORD=changeme_in_production
POSTGRES_DB=second_brain

# Docker user permissions (auto-detect on Linux/macOS)
# Ensures files created by container match your user
USER_ID=1000  # Run `id -u` to get your user ID
GROUP_ID=1000  # Run `id -g` to get your group ID

# API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GOOGLE_API_KEY=...

# Vault (adjust to your actual path)
OBSIDIAN_VAULT_PATH=/Users/tijlkoenderink/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian-Private

# Calendar
CALENDAR_WORK_URL=https://...
CALENDAR_PRIVATE_URL=https://...

# Encryption
API_KEY_ENCRYPTION_KEY=...
```

**Create Docker deployment scripts**

```bash
# scripts/docker-build.sh
#!/bin/bash
set -e

echo "Building Docker images..."
docker-compose build --parallel

echo "Done! Run 'docker-compose up' to start services."

# scripts/docker-start.sh
#!/bin/bash
set -e

# Load environment
if [ ! -f .env ]; then
    echo "Creating .env from .env.docker..."
    cp .env.docker .env
    echo "⚠️  Please edit .env with your actual values!"
    exit 1
fi

echo "Starting Second Brain services..."
docker-compose up -d

echo ""
echo "Services starting..."
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Check status: docker-compose ps"
echo "View logs:    docker-compose logs -f"
echo "Stop all:     docker-compose down"

# scripts/docker-stop.sh
#!/bin/bash
docker-compose down

# scripts/docker-logs.sh
#!/bin/bash
docker-compose logs -f $@
```

**Make scripts executable**

```bash
chmod +x scripts/docker-*.sh
```

**Test Docker Deployment**

```bash
# 1. Build images
./scripts/docker-build.sh

# 2. Start services
./scripts/docker-start.sh

# 3. Check health
curl http://localhost:8000/health
open http://localhost:3000

# 4. Run tests against Docker
cd services/brain_runtime
API_URL=http://localhost:8000 uv run pytest tests/integration/

# 5. View logs
./scripts/docker-logs.sh backend

# 6. Stop
./scripts/docker-stop.sh
```

**Document Docker Deployment**

```markdown
# docs/DOCKER_DEPLOYMENT.md

# Docker Deployment Guide

## Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- 4GB RAM minimum
- 10GB disk space

## Quick Start

1. Configure environment:
```bash
cp .env.docker .env
# Edit .env with your API keys and vault path
```

2. Build and start:
```bash
./scripts/docker-build.sh
./scripts/docker-start.sh
```

3. Access:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Architecture

```
┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │
│ (Next.js)   │     │  (FastAPI)  │
│  Port 3000  │     │  Port 8000  │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────┼──────┐
                    │      │      │
              ┌─────▼──┐ ┌─▼────┐ ┌────────┐
              │Postgres│ │Chroma│ │ Vault  │
              │  5432  │ │ 8001 │ │(mount) │
              └────────┘ └──────┘ └────────┘
```

## Volume Mounts

- `postgres_data`: Database persistence
- `chroma_data`: Vector store persistence
- `backend_data`: Logs, cache, secrets
- Vault: Read-only mount from host

## Monitoring

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f backend

# Check resource usage
docker stats

# Check health
curl http://localhost:8000/health
```

## Backup

```bash
# Database
docker-compose exec postgres pg_dump -U secondbrain second_brain > backup.sql

# Vector store
docker-compose exec chromadb tar czf - /chroma/chroma > chroma-backup.tar.gz

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U secondbrain second_brain
```

## Troubleshooting

### Port already in use
```bash
# Find process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Database connection error
```bash
# Reset database
docker-compose down -v
docker-compose up -d postgres
sleep 10
docker-compose up -d
```

### Vault not accessible
- Ensure OBSIDIAN_VAULT_PATH in .env is correct
- Check Docker has file sharing enabled for that path
- On macOS: Docker → Settings → Resources → File Sharing

## Production Deployment

For production on home PC:

1. Change passwords in .env
2. Set up reverse proxy (nginx) for HTTPS
3. Configure firewall
4. Set up automatic backups
5. Monitor with docker stats or Prometheus

See PRODUCTION_DEPLOYMENT.md for details.
```

**Deliverables:**
- [ ] Dockerfile for backend
- [ ] Dockerfile for frontend
- [ ] docker-compose.yml
- [ ] Docker scripts
- [ ] DOCKER_DEPLOYMENT.md
- [ ] Successfully tested Docker deployment
- [ ] Commit: "feat: add Docker deployment"

**🎉 END OF WEEK 3: PRODUCTION-READY**

**Status:**
- ✅ 70% test coverage
- ✅ Docker deployment working
- ✅ All critical paths tested
- ✅ Can deploy to any machine

---

## WEEK 4: PERFORMANCE + POLISH (Days 16-20)
**Goal:** Optimize performance, final polish for solid MVP

### Day 16: Performance Optimization - Backend (6 hours)

**Fix Blocking I/O**

```python
# 1. Install aiofiles
# Add to pyproject.toml: aiofiles>=23.0.0

# 2. Replace blocking file operations in api/vault.py
import aiofiles

# Before (blocking):
content = file_path.read_text(encoding="utf-8")

# After (async):
async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
    content = await f.read()

# Also fix in:
# - core/proposal_service.py
# - core/skill_loader.py (if applicable)
```

**Add In-Memory Caching**

```python
# core/cache.py
from functools import lru_cache
from typing import Dict, Any
import time

class SimpleCache:
    """In-memory TTL cache"""
    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Any | None:
        if key in self._cache:
            value, expires = self._cache[key]
            if time.time() < expires:
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any):
        self._cache[key] = (value, time.time() + self._ttl)

    def clear(self):
        self._cache.clear()

# Global cache instance
cache = SimpleCache(ttl=300)  # 5 minutes

# Use in skills loading (core/skill_loader.py)
async def load_skill_metadata(skill_id: str):
    cache_key = f"skill_meta:{skill_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Load from DB
    skill = await db.query(UserSkillDB).filter(...).first()
    cache.set(cache_key, skill)
    return skill
```

**Add Pagination**

```python
# In core/session_service.py
async def load_messages(
    self,
    session_id: uuid.UUID,
    limit: int = 100,  # Default limit
    offset: int = 0
) -> list[ChatMessage]:
    """Load messages with pagination"""
    result = await self.db.execute(
        select(ChatMessageDB)
        .where(ChatMessageDB.session_id == session_id)
        .order_by(ChatMessageDB.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    messages = result.scalars().all()
    return [ChatMessage.from_db(msg) for msg in reversed(messages)]

# Update API endpoint
@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str,
    limit: int = Query(100, le=1000),  # Max 1000
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    service = SessionService(db)
    messages = await service.load_messages(
        uuid.UUID(session_id),
        limit=limit,
        offset=offset
    )
    return messages
```

**Add Database Indexes**

```sql
-- migrations/006_add_indexes.sql

-- Chat queries
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
ON chat_messages(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_created
ON chat_sessions(created_at DESC);

-- Proposal queries
CREATE INDEX IF NOT EXISTS idx_proposals_status
ON proposals(status);

-- Skill queries
CREATE INDEX IF NOT EXISTS idx_skills_category
ON user_skills(category);

-- Full-text search on skills
CREATE INDEX IF NOT EXISTS idx_skills_search
ON user_skills USING gin(to_tsvector('english', name || ' ' || description));
```

**Benchmark Improvements**

```bash
# Before/after comparison
# Use Apache Bench
ab -n 100 -c 10 http://localhost:8000/health

# Profile slow endpoints
uv run python -m cProfile -s cumtime main.py
```

**Deliverables:**
- [ ] Blocking I/O fixed (use aiofiles)
- [ ] Caching implemented
- [ ] Pagination added
- [ ] Database indexes added
- [ ] Performance benchmarks documented
- [ ] Commit: "perf: optimize backend performance"

---

### Day 17: Performance Optimization - Frontend (6 hours)

**Refactor useChat Hook**

```typescript
// Split useChat.ts into smaller hooks

// src/hooks/useStreamingChat.ts
export function useStreamingChat() {
  // Just streaming logic
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  // ...
  return { isStreaming, streamingText, ... }
}

// src/hooks/useSessionManagement.ts
export function useSessionManagement() {
  // Just session CRUD
  const [sessions, setSessions] = useState([])
  const createSession = async () => { ... }
  // ...
  return { sessions, createSession, ... }
}

// src/hooks/useChat.ts (simplified)
export function useChat() {
  const streaming = useStreamingChat()
  const session = useSessionManagement()
  // Compose the two
  return { ...streaming, ...session }
}
```

**Use useReducer for Complex State**

```typescript
// src/hooks/useChatState.ts
type ChatState = {
  messages: Message[]
  toolCalls: ToolCall[]
  toolResults: ToolResult[]
  proposals: Proposal[]
  isStreaming: boolean
}

type ChatAction =
  | { type: 'ADD_MESSAGE'; message: Message }
  | { type: 'ADD_TOOL_CALL'; toolCall: ToolCall }
  | { type: 'ADD_TOOL_RESULT'; result: ToolResult }
  | { type: 'START_STREAMING' }
  | { type: 'STOP_STREAMING' }
  | { type: 'RESET' }

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.message] }
    case 'START_STREAMING':
      return { ...state, isStreaming: true }
    case 'STOP_STREAMING':
      return { ...state, isStreaming: false }
    // ... etc
    default:
      return state
  }
}

export function useChatState() {
  const [state, dispatch] = useReducer(chatReducer, initialState)
  return { state, dispatch }
}
```

**Add Debouncing**

```typescript
// src/hooks/useDebounce.ts
import { useEffect, useState } from 'react'

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(handler)
  }, [value, delay])

  return debouncedValue
}

// Use in page.tsx
const debouncedIsMobile = useDebounce(isMobile, 250)
```

**Add Virtual Scrolling**

```typescript
// Install react-window
pnpm add react-window

// src/components/chat/VirtualizedMessageList.tsx
import { FixedSizeList } from 'react-window'

export function VirtualizedMessageList({ messages }: { messages: Message[] }) {
  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <MessageBubble message={messages[index]} />
    </div>
  )

  return (
    <FixedSizeList
      height={600}
      itemCount={messages.length}
      itemSize={100}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  )
}
```

**Memoize Expensive Components**

```typescript
// src/components/chat/MessageBubble.tsx
import { memo } from 'react'

export const MessageBubble = memo(function MessageBubble({ message, isStreaming }) {
  // Component logic
}, (prevProps, nextProps) => {
  // Custom comparison
  return prevProps.message.id === nextProps.message.id &&
         prevProps.isStreaming === nextProps.isStreaming
})
```

**Bundle Size Analysis**

```bash
# Analyze bundle
cd apps/web
pnpm build
pnpm analyze  # If you have @next/bundle-analyzer

# Check for large dependencies
npx source-map-explorer .next/static/**/*.js
```

**Deliverables:**
- [ ] useChat split into smaller hooks
- [ ] useReducer for complex state
- [ ] Debouncing added
- [ ] Virtual scrolling (if needed)
- [ ] React.memo for pure components
- [ ] Bundle size analyzed
- [ ] Commit: "perf: optimize frontend performance"

---

### Day 18: Documentation + Deployment Guide (6 hours)

**Update CLAUDE.md**

```markdown
# Key updates:
- Change Phase 10 status: "🔄 Spec" → "✅ Complete"
- Add "Building solid MVP for personal use"
- Document Python environment quirk (uv run vs uv pip)
- Add Docker deployment section
- Update troubleshooting with common issues
- Add performance benchmarks
```

**Create Production Deployment Guide**

```markdown
# docs/PRODUCTION_DEPLOYMENT.md

# Production Deployment on Home PC

## Hardware Requirements

- CPU: 4+ cores (Intel i5/AMD Ryzen 5 or better)
- RAM: 8GB minimum, 16GB recommended
- Storage: 50GB SSD (for OS + Docker + data)
- Network: 100+ Mbps for remote access

## Operating System

Tested on:
- Ubuntu 22.04 LTS (recommended)
- macOS 13+ (Ventura)
- Windows 11 with WSL2

## Installation Steps

### 1. Install Docker

**Ubuntu:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS:**
```bash
brew install --cask docker
open /Applications/Docker.app
```

### 2. Clone Repository

```bash
cd ~/
git clone <your-repo-url> second-brain-app
cd second-brain-app
```

### 3. Configure Environment

```bash
cp .env.docker .env
nano .env  # Edit with your values
```

### 4. Build and Deploy

```bash
./scripts/docker-build.sh
./scripts/docker-start.sh
```

### 5. Verify

```bash
curl http://localhost:8000/health
open http://localhost:3000
```

## Remote Access (Tailscale)

### Why Tailscale?

- Secure mesh VPN
- No port forwarding
- Works behind NAT
- Free for personal use

### Setup

1. Install Tailscale:
```bash
# Ubuntu
curl -fsSL https://tailscale.com/install.sh | sh

# macOS
brew install tailscale
```

2. Authenticate:
```bash
sudo tailscale up
```

3. Get Tailscale IP:
```bash
tailscale ip -4
# Example: 100.64.1.2
```

4. Access from anywhere:
```
http://100.64.1.2:3000
```

### Secure with HTTPS

```bash
# Install Caddy (automatic HTTPS)
docker run -d \
  -p 443:443 \
  -v caddy_data:/data \
  -v caddy_config:/config \
  caddy:latest \
  caddy reverse-proxy \
  --from https://brain.yourdomain.com \
  --to localhost:3000
```

## Monitoring

### Resource Usage

```bash
# Check Docker stats
docker stats

# Check disk usage
docker system df

# Clean up
docker system prune -a
```

### Logs

```bash
# View all logs
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Uptime Monitoring

```bash
# Install uptime-kuma
docker run -d \
  --name=uptime-kuma \
  -p 3001:3001 \
  -v uptime-kuma:/app/data \
  louislam/uptime-kuma:1

# Access at http://localhost:3001
```

## Backup Strategy

### Automated Daily Backup

```bash
# Create backup script
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d)

# Database
docker-compose exec -T postgres pg_dump -U secondbrain second_brain | gzip > "$BACKUP_DIR/db-$DATE.sql.gz"

# Chroma
docker-compose exec chromadb tar czf - /chroma/chroma > "$BACKUP_DIR/chroma-$DATE.tar.gz"

# Keep last 7 days
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete
EOF

chmod +x scripts/backup.sh

# Add to cron (run daily at 2 AM)
echo "0 2 * * * /home/user/second-brain-app/scripts/backup.sh" | crontab -
```

## Troubleshooting

### Container won't start

```bash
docker-compose logs backend
docker-compose down
docker-compose up -d
```

### Out of memory

```bash
# Check memory
free -h

# Increase swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Database corruption

```bash
# Restore from backup
docker-compose down
docker volume rm second-brain-app_postgres_data
docker-compose up -d postgres
sleep 10
gunzip -c backup.sql.gz | docker-compose exec -T postgres psql -U secondbrain second_brain
docker-compose up -d
```

## Security Checklist

- [ ] Change default passwords
- [ ] Use strong API encryption key
- [ ] Enable firewall (ufw/iptables)
- [ ] Keep Docker updated
- [ ] Regular backups
- [ ] Monitor logs for suspicious activity
- [ ] Use Tailscale for remote access (not port forwarding)

## Performance Tuning

### Postgres

```bash
# Edit postgresql.conf
docker-compose exec postgres bash
nano /var/lib/postgresql/data/postgresql.conf

# Increase:
shared_buffers = 256MB
effective_cache_size = 1GB
```

### Next.js

```bash
# Enable compression
# Add to next.config.ts:
compress: true
```

## Updates

```bash
# Pull latest code
git pull

# Rebuild containers
docker-compose build --no-cache

# Restart
docker-compose down
docker-compose up -d
```
```

**Create User Guide**

```markdown
# docs/USER_GUIDE.md

# Second Brain User Guide

## Getting Started

### First Launch

1. Open http://localhost:3000
2. Click "New Chat"
3. Select persona (or leave as "Tools" mode)
4. Start chatting!

### Personas

**Socratic (🏛️)** - Questions your assumptions
- Use when: Making important decisions
- Specialty: Uncovering hidden beliefs
- Example: "Should I take this job?"

**Contrarian (😈)** - Finds weaknesses
- Use when: Stress-testing ideas
- Specialty: Risk identification
- Example: "What could go wrong with this plan?"

**Pragmatist (🎯)** - Drives to action
- Use when: Need to get unstuck
- Specialty: 80/20 thinking
- Example: "How do I prioritize these tasks?"

**Synthesizer (🔮)** - Finds connections
- Use when: Exploring complex topics
- Specialty: Pattern recognition
- Example: "How do these concepts relate?"

**Coach (🌱)** - Supportive guidance
- Use when: Need encouragement
- Specialty: Growth mindset
- Example: "I'm struggling with motivation"

### Invoking Councils

Decision Council (Socratic + Contrarian + Pragmatist):
```
"Should I quit my job to start a startup? Invoke Decision Council."
```

The council will:
1. Ask clarifying questions (Socratic)
2. Identify risks (Contrarian)
3. Suggest concrete next steps (Pragmatist)
4. Synthesize into balanced advice

### Using Skills

Skills enhance the AI's capabilities:

**Automatic:** Skills are auto-attached based on conversation
**Manual:** Click "Skills" panel to enable/disable

Categories:
- Knowledge (research, analysis)
- Workflow (productivity, organization)
- Analysis (decision-making)
- Creation (writing, ideation)
- Council (multi-persona)

### Write Mode (Proposals)

When the AI suggests file changes:

1. Review the proposal
2. See diff (red = removed, green = added)
3. Click "Accept" or "Reject"
4. File is updated in your vault

### Vault Integration

Your Obsidian vault is read-only by default.

**Search files:**
```
"Search my vault for notes about Python"
```

**Read specific file:**
```
"Read the contents of Projects/Second Brain.md"
```

**Semantic search:**
```
"Find notes similar to: machine learning concepts"
```

### Calendar & Tasks

Synced from your vault:

**View today:**
```
"What's on my calendar today?"
```

**Task summary:**
```
"Show me my overdue tasks"
```

**Week ahead:**
```
"What meetings do I have this week?"
```

## Tips & Tricks

### Best Practices

1. **Be specific**: "Help me write a Python function to parse JSON" vs "Help with Python"
2. **Invoke councils for big decisions**: "Invoke Decision Council" for multi-perspective analysis
3. **Attach context files**: Select vault files relevant to your question
4. **Use personas**: Different personas for different thinking styles
5. **Review proposals carefully**: Always check diffs before accepting

### Keyboard Shortcuts

- `Cmd/Ctrl + K` - New chat
- `Cmd/Ctrl + /` - Focus message input
- `Esc` - Close modals
- `Enter` - Send message
- `Shift + Enter` - New line in message

### Common Workflows

**Research workflow:**
1. Start with Synthesizer persona
2. Ask broad question
3. Attach related vault files
4. Use "pattern recognition" skill

**Decision workflow:**
1. Frame decision clearly
2. Invoke Decision Council
3. Follow up with specific personas for depth
4. Document decision in vault

**Writing workflow:**
1. Use Coach or Pragmatist
2. Outline first
3. Request proposal for new file
4. Iterate with edits

## Troubleshooting

### Chat not responding

1. Check backend: http://localhost:8000/health
2. Check browser console (F12)
3. Refresh page

### Proposals not showing

1. Ensure vault path is correct
2. Check write permissions
3. View logs: `docker-compose logs backend`

### Skills not loading

1. Check ~/.claude/skills/ directory
2. Verify YAML syntax
3. Restart backend

### Performance slow

1. Check Docker resources
2. Clear old sessions (Settings → Clear History)
3. Reduce attached context files

## Advanced

### Custom Skills

Create custom skills in ~/.claude/skills/:

```yaml
# ~/.claude/skills/my-skill/SKILL.md
---
name: My Custom Skill
description: Does something useful
category: custom
when_to_use: When user needs X
---

# My Custom Skill

## How to Use

1. Step one
2. Step two
```

### API Access

```bash
# Direct API calls
curl http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
```

### Backup & Export

```bash
# Export chat history
curl http://localhost:8000/sessions > sessions-backup.json

# Backup database
docker-compose exec postgres pg_dump second_brain > backup.sql
```
```

**Deliverables:**
- [ ] CLAUDE.md updated
- [ ] PRODUCTION_DEPLOYMENT.md created
- [ ] USER_GUIDE.md created
- [ ] All documentation proofread
- [ ] Commit: "docs: complete production documentation"

---

### Day 19-20: Final Polish + Release (12 hours)

**Code Cleanup**

```bash
# 1. Remove all console.log in production
# Find them:
grep -r "console\\.log" apps/web/src --include="*.tsx" --include="*.ts"

# Replace with proper logging or remove

# 2. Remove commented code
# Manual review and cleanup

# 3. Ensure all TODOs are tracked or removed
grep -r "TODO\|FIXME" --include="*.py" --include="*.ts" --include="*.tsx"
```

**Configuration Hardening**

```python
# core/config.py - Production settings
class Settings(BaseSettings):
    environment: str = Field(default="development", env="ENVIRONMENT")

    # Stricter CORS in production
    @property
    def cors_origins(self) -> list[str]:
        if self.environment == "production":
            return ["https://yourdomain.com"]
        return ["http://localhost:3000"]

    # Disable debug in production
    @property
    def debug(self) -> bool:
        return self.environment != "production"
```

**Security Audit**

```bash
# 1. Check for secrets
git secrets --scan  # or use gitleaks

# 2. Verify .gitignore
cat .gitignore | grep -E "(\.env|secrets|\.key)"

# 3. Review exposed endpoints
curl http://localhost:8000/openapi.json | jq '.paths | keys'

# 4. Test rate limiting
ab -n 200 -c 20 http://localhost:8000/health
# Should see 429 responses after limits
```

**Performance Baseline**

```bash
# Document performance metrics
cat > docs/PERFORMANCE_BASELINE.md << 'EOF'
# Performance Baseline - v0.9 MVP

Measured: 2025-12-23
Hardware: MacBook Pro M1, 16GB RAM
Database: 1000 chat messages, 50 skills

## Response Times (p50/p95/p99)

- Health check: 5ms / 10ms / 15ms
- Chat (simple): 800ms / 1.2s / 1.5s
- Chat (with tools): 2s / 3.5s / 5s
- Council invocation: 8s / 12s / 15s
- Vault search: 100ms / 200ms / 300ms

## Resource Usage

- Memory (backend): 250MB idle, 400MB peak
- Memory (frontend): 100MB
- CPU (idle): <5%
- CPU (active chat): 40-60%

## Database

- Connection pool: 10 connections
- Query avg: <50ms
- Indexes: All critical paths

## Optimization Targets

- Chat response: <1s (p95)
- Council: <10s (p95)
- Search: <100ms (p95)
EOF
```

**Release Checklist**

```markdown
# docs/RELEASE_CHECKLIST.md

# v0.9 MVP Release Checklist

## Pre-Release

- [ ] All tests passing (70% coverage)
- [ ] No linter warnings
- [ ] No console errors in browser
- [ ] Docker build successful
- [ ] Documentation complete
- [ ] CHANGELOG.md updated
- [ ] Version bumped in package.json

## Testing

- [ ] Manual smoke test (critical paths)
- [ ] E2E tests passing
- [ ] Integration tests passing
- [ ] Performance baseline documented
- [ ] Security audit passed

## Deployment

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] Backups configured
- [ ] Monitoring enabled
- [ ] Docker containers healthy

## Post-Release

- [ ] Verify health endpoint
- [ ] Test chat interface
- [ ] Test persona selection
- [ ] Invoke Decision Council
- [ ] Accept a proposal
- [ ] Search vault
- [ ] Monitor logs (24 hours)

## Rollback Plan

If issues:
1. docker-compose down
2. Restore database: gunzip -c backup.sql.gz | docker exec -i postgres psql
3. docker-compose up -d
4. Investigate logs
5. Fix and redeploy
```

**Create CHANGELOG**

```markdown
# CHANGELOG.md

# Changelog

All notable changes to Second Brain System.

## [0.9.0] - 2025-12-23

### Added

**Phase 10: Council & Persona System**
- 5 personas with distinct reasoning styles (Socratic, Contrarian, Pragmatist, Synthesizer, Coach)
- 8 persona-specific skills
- 3 council skills (Decision, Research, Creative)
- Tool-based council architecture
- Multi-vendor LLM support via LiteLLM

**Testing**
- Comprehensive test suite (70% coverage)
- Backend unit tests (pytest)
- Frontend component tests (Vitest)
- E2E tests (Playwright)
- Integration tests

**Deployment**
- Docker containerization
- docker-compose orchestration
- Production deployment guide
- Automated backups
- Health checks

**Performance**
- Async file I/O (aiofiles)
- In-memory caching
- Database indexes
- Pagination
- Virtual scrolling (frontend)

**Security**
- Rate limiting (slowapi)
- Restricted CORS
- API key masking
- Error boundaries

**Documentation**
- SYSTEM_DEFINITION_v0.9.md
- COMPREHENSIVE_REVIEW_2025-12-23.md
- DOCKER_DEPLOYMENT.md
- PRODUCTION_DEPLOYMENT.md
- USER_GUIDE.md
- PYTHON_ENVIRONMENT.md

### Fixed
- Python environment confusion (uv run vs uv pip)
- Linter warnings (unused imports, boolean comparisons)
- Frontend ESLint warnings
- Error handling gaps
- Blocking I/O operations

### Changed
- CLAUDE.md updated (Phase 10: Complete)
- Test coverage from <5% to 70%
- Error handling now comprehensive
- Performance improvements (2x faster average response)

## [0.8.0] - Previous Release

(Phases 1-9 - see git history)
```

**Git Tag Release**

```bash
# Clean commit
git add .
git commit -m "release: v0.9.0 MVP with full test coverage and Docker"

# Tag
git tag -a v0.9.0 -m "Second Brain v0.9 MVP

- Phase 10 complete (councils & personas)
- 70% test coverage
- Docker deployment
- Production-ready
"

# Push
git push
git push --tags
```

**Celebrate! 🎉**

```bash
# Final verification
docker-compose up -d
curl http://localhost:8000/health
open http://localhost:3000

# You now have a solid, tested, deployable MVP!
```

**Deliverables:**
- [ ] Code cleanup complete
- [ ] Security audit passed
- [ ] Performance baseline documented
- [ ] CHANGELOG.md created
- [ ] Release checklist completed
- [ ] Git tagged v0.9.0
- [ ] Commit: "release: v0.9.0 MVP"

**🎉 END OF WEEK 4: SOLID MVP COMPLETE**

**Final Status:**
- ✅ 70% test coverage
- ✅ Docker deployment
- ✅ Performance optimized
- ✅ Fully documented
- ✅ Production-ready
- ✅ Personal use MVP achieved

---

## ONGOING MAINTENANCE

After Week 4, continue with:

### Weekly
- Run test suite
- Check logs for errors
- Review monitoring dashboard
- Update dependencies (pnpm update, uv sync)

### Monthly
- Security updates (docker pull)
- Performance review
- Backup verification
- Documentation updates

### Quarterly
- Feature planning
- Architecture review
- Test coverage audit
- Performance benchmarks

---

## SUCCESS METRICS

### Week 1 ✅
- Phase 10 verified and working
- Basic error handling
- 15% test coverage
- You can use the system

### Week 2 ✅
- 40% test coverage
- Monitoring dashboard
- Bug fixes
- Confident in stability

### Week 3 ✅
- 70% test coverage
- Docker deployment
- Production-ready
- Can deploy anywhere

### Week 4 ✅
- Performance optimized
- Fully documented
- Solid MVP
- Ready for daily use

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Tests take too long | Parallelize with pytest-xdist, run slow tests separately |
| Docker issues | Test on multiple machines early |
| Performance regression | Benchmark before/after, automated performance tests |
| Breaking changes | Comprehensive tests catch regressions |
| Deployment failure | Rollback plan, automated backups |

---

## COST ESTIMATE

**Time:**
- Week 1: 25 hours (critical path)
- Week 2: 30 hours (testing expansion)
- Week 3: 30 hours (full coverage + Docker)
- Week 4: 25 hours (polish)
- **Total: 110 hours (14 working days)**

**Actual Calendar:**
- If full-time: 3 weeks
- If part-time (4h/day): 5-6 weeks
- If evenings (2h/day): 10-12 weeks

**Resources:**
- Developer time only (no cloud costs)
- Local development (existing hardware)
- Total cost: $0 (excluding time)

---

## APPENDIX: Docker Deep Dive

### Why Docker?

**Problems it solves:**
1. **Python version hell** - Container has exact Python 3.11
2. **Dependency conflicts** - Isolated environment
3. **Deployment consistency** - Same environment everywhere
4. **Easy backup** - Volume snapshots
5. **Portability** - Works on any machine with Docker

**How it works:**

```
Host Machine (macOS/Linux/Windows)
│
├── Docker Engine
│   ├── Container: Frontend (Next.js)
│   │   └── Node 20, Next.js 15, app code
│   │
│   ├── Container: Backend (FastAPI)
│   │   └── Python 3.11, FastAPI, app code
│   │
│   ├── Container: PostgreSQL
│   │   └── Postgres 16, data volume
│   │
│   └── Container: ChromaDB
│       └── Chroma server, vector volume
│
└── Volumes (persistent data)
    ├── postgres_data (database)
    ├── chroma_data (vectors)
    └── backend_data (logs, cache)
```

### Dockerfile Explained

```dockerfile
# Start from base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y postgresql-client

# Install Python dependencies
COPY pyproject.toml .
RUN uv sync

# Copy application code
COPY . .

# Expose port (documentation only)
EXPOSE 8000

# Command to run when container starts
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0"]
```

### docker-compose.yml Explained

```yaml
services:
  # Service definition
  backend:
    # Build from Dockerfile
    build: ./services/brain_runtime

    # Depends on other services
    depends_on:
      - postgres  # Wait for postgres to be healthy

    # Environment variables
    environment:
      DATABASE_URL: postgresql://user@postgres:5432/db

    # Volume mounts
    volumes:
      - backend_data:/app/data  # Named volume
      - /host/path:/container/path:ro  # Bind mount (read-only)

    # Port mapping (host:container)
    ports:
      - "8000:8000"

    # Restart policy
    restart: unless-stopped
```

### Volume Types

**Named Volumes** (managed by Docker):
```yaml
volumes:
  - postgres_data:/var/lib/postgresql/data
```
- Location: `/var/lib/docker/volumes/`
- Persist across container rebuilds
- Easy to backup with `docker run --volumes-from`

**Bind Mounts** (host filesystem):
```yaml
volumes:
  - /Users/you/vault:/vault:ro
```
- Direct host path
- Real-time updates
- Used for vault (source of truth on host)

### Networking

Docker creates a private network for services:

```
frontend (container) -> backend:8000 (internal DNS)
backend (container) -> postgres:5432 (internal DNS)
host machine -> localhost:3000 -> frontend:3000 (port mapping)
```

**No need for localhost** inside containers - use service names!

### Data Persistence

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect second-brain-app_postgres_data

# Backup volume
docker run --rm \
  -v second-brain-app_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar czf /backup/postgres-backup.tar.gz /data

# Restore volume
docker run --rm \
  -v second-brain-app_postgres_data:/data \
  -v $(pwd):/backup \
  ubuntu tar xzf /backup/postgres-backup.tar.gz -C /
```

### Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1
```

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Benefits:**
- `depends_on` can wait for healthy (not just started)
- Docker will restart unhealthy containers
- `docker ps` shows health status

### Resource Limits

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Production vs Development

```yaml
# docker-compose.yml (base)
services:
  backend:
    build: .
    ports:
      - "8000:8000"

# docker-compose.prod.yml (override)
services:
  backend:
    build:
      args:
        BUILD_ENV: production
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

# Run production:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Debugging

```bash
# View logs
docker-compose logs -f backend

# Execute command in running container
docker-compose exec backend bash
docker-compose exec backend uv run pytest

# Inspect container
docker inspect second-brain-backend

# See processes
docker-compose top

# Resource usage
docker stats
```

### Cleanup

```bash
# Stop and remove containers
docker-compose down

# Remove volumes too (⚠️ deletes data!)
docker-compose down -v

# Remove unused images
docker image prune -a

# Nuclear option (⚠️ removes everything!)
docker system prune -a --volumes
```

### Home PC Deployment

**Advantages:**
1. **Always on** - No need to start dev servers manually
2. **Portable** - Move to different PC easily
3. **Consistent** - Same environment as development
4. **Secure** - No cloud, full control
5. **Free** - No hosting costs

**Setup on Ubuntu home server:**

```bash
# 1. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 2. Clone repo
git clone <your-repo> ~/second-brain-app
cd ~/second-brain-app

# 3. Configure
cp .env.docker .env
nano .env

# 4. Deploy
./scripts/docker-start.sh

# 5. Set up autostart (systemd)
sudo cat > /etc/systemd/system/second-brain.service << 'EOF'
[Unit]
Description=Second Brain App
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/user/second-brain-app
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=user

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable second-brain
sudo systemctl start second-brain

# 6. Access via Tailscale
sudo tailscale up
tailscale ip -4  # Get your Tailscale IP

# From any device on Tailscale:
# http://<tailscale-ip>:3000
```

**Power Management:**

```bash
# Disable sleep (server stays on)
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

# Or schedule wake/sleep:
# Wake at 6 AM, sleep at 11 PM
echo "0 6 * * * sudo systemctl start second-brain" | crontab -
echo "0 23 * * * sudo systemctl stop second-brain" | crontab -
```

---

## SUMMARY

**Scenario 3 delivers:**
- ✅ Personal MVP in Week 1
- ✅ Full 70% test coverage (not just 50%)
- ✅ Docker deployment ready
- ✅ Performance optimized
- ✅ Production-quality documentation
- ✅ Solid foundation for daily use

**No accessibility work** - Acceptable for personal use only.

**Timeline: 4 weeks (110 hours)**

**Ready to start?** Begin with Day 1: Python Environment + Linter! 🚀
