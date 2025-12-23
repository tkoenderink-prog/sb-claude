# Scenario 3 Implementation Plan - Updates

**Date:** 2025-12-23
**Changes:** Docker fixes + Application Git + Vault Git Management

---

## Summary of Changes

### 1. Fixed Critical Docker Issue: Read-Only Vault Mount ❌→✅

**Problem Identified:**
```yaml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault:ro"  # ❌ Read-only blocks writes!
```

**Impact:** Breaks entire Phase 8 proposal system:
- ❌ Proposals can't be applied
- ❌ YOLO mode doesn't work
- ❌ `write_vault_file` tool fails

**Solution:**
```yaml
volumes:
  - "${OBSIDIAN_VAULT_PATH}:/vault"  # ✅ Read-write for proposals
```

**Safety:** Application-level safety layers remain:
- Write mode requires approval
- YOLO mode is explicit user choice
- Path sandboxing prevents writes outside vault
- Vault should be in git for backup

---

### 2. Fixed Docker File Permissions

**Problem:** Docker container runs as root → files owned by root on host

**Solution:**
```dockerfile
# Create non-root user matching host UID/GID
ARG USER_ID=1000
ARG GROUP_ID=1000
RUN groupadd -g ${GROUP_ID} app && \
    useradd -u ${USER_ID} -g app -m -s /bin/bash app
USER app
```

**Usage:**
```bash
# In .env
USER_ID=$(id -u)  # Auto-detect: 1000
GROUP_ID=$(id -g)  # Auto-detect: 1000
```

**Result:** Files created by Docker match your user ownership

---

### 3. Added Application Git Setup (Week 1, Day 5)

**New Feature:** Version control the second-brain-app codebase itself

**What's Added:**
- Comprehensive `.gitignore` (secrets, data, logs, build artifacts)
- Initialize git repository
- Push to GitHub (via `gh` CLI)
- Create development branch

**Time:** 1 hour (part of Day 5)

**Benefits:**
- Protects all development work
- Enables collaboration later
- Safe rollback if something breaks

**Example:**
```bash
git init
git add .
git commit -m "Initial commit: Second Brain v0.9"
gh repo create second-brain-app --private --source=. --remote=origin
git push -u origin main
```

---

### 4. Added Vault Git Management (Week 2, Day 7) - NEW FEATURE ⭐

**What:** UI-driven git management for Obsidian vault with auto-commit on edits

**Components:**

#### Backend (5 hours):
1. **VaultGitService** (`core/git_service.py`)
   - `get_status()` - Returns git status, last commit, uncommitted files
   - `commit_changes()` - Commits specific files or all changes
   - `sync()` - Pull → commit → push workflow
   - `get_diff()` - Show diffs for review

2. **API Endpoints** (`api/vault_git.py`)
   - `GET /vault/git/status` - Current status
   - `POST /vault/git/sync` - Commit & push
   - `GET /vault/git/diff` - View changes

3. **Proposal Integration**
   - Before edit: Commit checkpoint
   - After edit: Commit with description
   - Optional auto-push (configurable)

#### Frontend (4 hours):
1. **Health Dashboard** (`/health`)
   - New page showing system health
   - VaultGitCard - shows git status
   - SystemStatsCard - usage metrics
   - RecentActivityCard - recent sessions

2. **VaultGitCard Component**
   - Last commit info (author, time, message)
   - Uncommitted files count (max 3 shown)
   - Remote sync status (ahead/behind)
   - "Commit & Push" button

3. **Settings Panel**
   - Auto-commit on proposal apply (default: true)
   - Auto-push after commit (default: false)
   - Commit message template

#### User Experience:

**Health Dashboard:**
```
┌─────────────────────────────────────┐
│ 📦 Vault Git Status                 │
├─────────────────────────────────────┤
│ Last Commit:                        │
│ • 2 hours ago by tijlkoenderink     │
│ • "Add weekly review notes"         │
│                                     │
│ Uncommitted Changes: 3 files        │
│ • daily/2025-12-23.md (modified)    │
│ • projects/second-brain.md (mod)    │
│ • +1 more...                        │
│                                     │
│ [View Diff] [Commit & Push]         │
│                                     │
│ Remote: ✅ In sync with origin/main │
└─────────────────────────────────────┘
```

**Proposal Apply Flow (with auto-commit):**
```
User applies proposal
  ↓
1. Pre-edit checkpoint commit
   "Pre-edit: Update task documentation"
  ↓
2. Apply file changes
  ↓
3. Post-edit commit
   "[Second Brain] Applied: Update task documentation"
  ↓
4. Auto-push (if enabled)
   ✅ "Synced to GitHub"
```

#### Database Schema:
```sql
ALTER TABLE user_settings ADD COLUMN git_settings JSONB DEFAULT '{
  "auto_commit_on_edit": true,
  "auto_push": false,
  "commit_message_template": "[Second Brain] {action}"
}'::jsonb;
```

#### Dependencies:
```toml
# Add to pyproject.toml
dependencies = [
    "gitpython>=3.1.40",
]
```

**Total Time:** 9 hours (new Day 7)

---

## Updated Week 2 Structure

**Before:**
- Day 6: Monitoring (6h)
- Day 7-8: Backend testing (12h)
- Day 9-10: Frontend testing (12h)

**After:**
- Day 6: Monitoring (6h)
- **Day 7: Health Dashboard + Vault Git (9h)** ⭐ NEW
- Day 8-9: Backend testing (12h)
- Day 10: Frontend testing (6h)

**Total Week 2:** 33 hours (was 30 hours, +3 hours for git feature)

---

## Files Modified in Implementation Plan

### Docker Configuration:
1. **docker-compose.yml**
   - ❌ Removed `:ro` flag from vault mount
   - ✅ Added `USER_ID` and `GROUP_ID` build args

2. **Dockerfile (backend)**
   - ✅ Added non-root user creation
   - ✅ Added git system dependency
   - ✅ All COPY commands use `--chown=app:app`

3. **.env.docker**
   - ✅ Added `USER_ID` and `GROUP_ID` variables

### Day 5 (Git Setup):
- ✅ Added comprehensive .gitignore
- ✅ Git init + GitHub push workflow
- ✅ Branch protection setup

### Day 7 (NEW - Vault Git):
- ✅ Backend: VaultGitService
- ✅ Backend: API endpoints
- ✅ Frontend: Health dashboard page
- ✅ Frontend: VaultGitCard component
- ✅ Frontend: Git settings panel
- ✅ Integration: Proposal auto-commit

---

## Key Benefits

### Application Git (Day 5):
1. **Safety** - Can revert if changes break things
2. **Collaboration** - Easy to share/contribute later
3. **Deployment** - Clean separation of code vs data

### Vault Git Management (Day 7):
1. **Safety** - Auto-checkpoint before edits
2. **History** - Track all vault changes
3. **Sync** - Keep vault in sync across devices
4. **Visibility** - See uncommitted changes in dashboard
5. **Control** - Manual or auto commit/push

### Docker Fixes:
1. **Functionality** - Proposals actually work
2. **Permissions** - No root-owned files
3. **Security** - Non-root container user

---

## Timeline Impact

**Original Plan:** 4 weeks (110 hours)
**Updated Plan:** 4 weeks (113 hours)
**Added:** +3 hours for vault git feature

**Justification:** Vault git management is high-value:
- Prevents data loss from bad edits
- Already using git, just adds UI
- Natural fit with monitoring/dashboard week
- Minimal time investment for major safety

---

## Implementation Order

1. **Week 1, Day 5** (before beta)
   - Set up application git
   - Push to GitHub
   - Ensures code is safe

2. **Week 2, Day 7** (after monitoring)
   - Build health dashboard
   - Add vault git UI
   - Integrate with proposals

3. **Week 3, Day 15** (Docker)
   - Use fixed docker-compose.yml
   - Test read-write vault access
   - Verify file permissions

---

## Testing Checklist

### Docker:
- [ ] Build containers with USER_ID/GROUP_ID
- [ ] Apply proposal through Docker
- [ ] Verify vault file ownership matches host user
- [ ] Test git operations inside container

### Application Git:
- [ ] .gitignore excludes secrets/data
- [ ] Push to GitHub succeeds
- [ ] Development branch created

### Vault Git:
- [ ] Health dashboard loads
- [ ] Git status card shows correct info
- [ ] "Commit & Push" button works
- [ ] Auto-commit on proposal apply works
- [ ] Settings toggle auto-commit/push
- [ ] Handles non-git vaults gracefully

---

## Questions Answered

**Q: Why mount vault as read-write?**
A: Proposals need to write files. Application-level safety (approval flow) protects against bad writes.

**Q: What if vault files get corrupted?**
A: Git provides safety - every edit gets committed before/after. Can revert any change.

**Q: What if push fails (offline)?**
A: Changes saved locally. Dashboard shows "ahead of remote". Push when back online.

**Q: What if there are merge conflicts?**
A: Sync operation returns error. User must resolve manually (rare for single-user vault).

**Q: Do I need to use the git features?**
A: Application git: Yes, protects your code.
   Vault git: Optional - vault already in git, this adds UI convenience.

---

## Next Steps

To implement these changes:

1. **Immediate** (if implementing now):
   - Update docker-compose.yml and Dockerfile per plan
   - Add .gitignore and push to GitHub

2. **Week 2** (if following plan):
   - Follow Day 7 instructions for health dashboard
   - Install gitpython dependency
   - Implement VaultGitService + API
   - Build frontend components

3. **Testing**:
   - Verify proposals write to vault in Docker
   - Test git operations in dashboard
   - Confirm auto-commit on proposal apply

---

**Document Status:** Complete
**Implementation Plan:** Updated in `docs/SCENARIO_3_IMPLEMENTATION_PLAN.md`
**Ready to implement:** Yes - all changes documented
