# Database Migrations

This directory contains SQL migration scripts for the Second Brain database.

## Migration History

### 001_add_phase7_tables.sql
**Date:** 2025-12-20
**Applied:** Yes
**Purpose:** Add Phase 7 tables for chat sessions, messages, agent runs, and artifacts

**Tables Created:**
- `chat_sessions` - Stores chat session configurations (mode, provider, model, attached skills)
- `chat_messages` - Stores individual messages within chat sessions
- `agent_runs` - Stores autonomous agent execution runs with metrics
- `agent_artifacts` - Stores artifacts produced by agent runs

**Indexes Created:**
- `idx_chat_messages_session_id` - Fast lookup of messages by session
- `idx_chat_messages_created_at` - Chronological message ordering
- `idx_chat_sessions_created_at` - Chronological session listing
- `idx_agent_runs_status` - Filter runs by status
- `idx_agent_runs_started_at` - Chronological run ordering
- `idx_agent_artifacts_run_id` - Fast lookup of artifacts by run

**Foreign Keys:**
- `chat_messages.session_id` → `chat_sessions.id` (CASCADE DELETE)
- `agent_artifacts.run_id` → `agent_runs.id` (CASCADE DELETE)

**Triggers:**
- `update_chat_sessions_updated_at` - Auto-update `updated_at` timestamp on chat_sessions updates

## How to Apply Migrations

### Manual Application
```bash
psql -d second_brain -f migrations/001_add_phase7_tables.sql
```

### Verify Application
```bash
# List all tables
psql -d second_brain -c "\dt"

# Verify specific table structure
psql -d second_brain -c "\d chat_sessions"

# List all indexes
psql -d second_brain -c "SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename, indexname;"
```

## Database Schema Summary

### Current Table Count: 8
- `jobs` - Job execution tracking (Phase 1)
- `job_logs` - Job log entries (Phase 1)
- `calendar_events` - Calendar events from Google + M365 (Phase 3)
- `tasks` - Parsed tasks from Obsidian vault (Phase 4)
- `chat_sessions` - Chat sessions (Phase 7)
- `chat_messages` - Chat messages (Phase 7)
- `agent_runs` - Agent runs (Phase 7)
- `agent_artifacts` - Agent artifacts (Phase 7)

### Current Index Count: 34
- Primary keys: 8
- Foreign keys: 2
- Performance indexes: 24

## Future Migrations

When creating new migrations:

1. Use sequential numbering: `00X_description.sql`
2. Include rollback instructions in comments
3. Test migrations on a local database first
4. Document in this README after applying
5. Always use `IF NOT EXISTS` and `IF EXISTS` clauses for idempotency

## Rollback Instructions

### 001_add_phase7_tables.sql
```sql
-- Drop tables in reverse order (foreign keys first)
DROP TABLE IF EXISTS agent_artifacts CASCADE;
DROP TABLE IF EXISTS chat_messages CASCADE;
DROP TABLE IF EXISTS agent_runs CASCADE;
DROP TABLE IF EXISTS chat_sessions CASCADE;
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;
```

## Notes

- All tables use UUID primary keys via `gen_random_uuid()`
- All tables have `created_at` timestamps with timezone
- JSONB is used for flexible data storage (attached_skills, tool_calls, etc.)
- Foreign keys use CASCADE DELETE for referential integrity
- Indexes are created for common query patterns
