# Persona & Skills Inventory - Obsidian-Private

**Location**: `/Users/tijlkoenderink/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian-Private/.claude/`
**Format**: Claude Agent SDK compatible
**Discovery Date**: 2026-01-02 (Phase 0)

---

## 📊 Summary

| Category | Count | Location | Format |
|----------|-------|----------|--------|
| **Personas** | **52** | `.claude/agents/` | AGENT.md files |
| **Skills** | **34** | `.claude/skills/` | SKILL.md files |

---

## 🎭 Personas (52 total)

**Path**: `Obsidian-Private/.claude/agents/`

### Sample Personas Discovered:
1. adam-grant.md
2. alex-hormozi.md
3. andrew-huberman.md
4. bessel-van-der-kolk.md
5. bj-fogg.md
6. brene-brown.md
7. buddha.md
8. cal-newport.md
9. calendar-assistant.md
10. dan-martell.md
11. document-classifier.md
12. esther-perel.md
13. frederic-laloux.md
14. gabor-mate.md
15. garrett-white.md
16. ... (37 more)

### Persona Categories:
- **Thought Leaders**: adam-grant, brene-brown, cal-newport, etc.
- **Health & Wellness**: andrew-huberman, bessel-van-der-kolk, gabor-mate
- **Business**: alex-hormozi, dan-martell, garrett-white
- **Spiritual**: buddha
- **Utility Agents**: calendar-assistant, document-classifier

---

## 🛠️ Skills (34 total)

**Path**: `Obsidian-Private/.claude/skills/`

### Key Skills:
- **call-council**: Multi-persona consultation orchestration
- ... (33 additional skills)

### Skill Categories:
- **Council Skills**: call-council (enables multi-persona consultations)
- **Workflow Skills**: TBD (needs Phase 1 inventory)
- **Analysis Skills**: TBD
- **Knowledge Skills**: TBD

---

## 🔗 Integration Points

### Phase 6: Claude Agent SDK Integration
The SDK's auto-discovery feature will:
```python
from claude_agent_sdk import ClaudeAgentOptions

options = ClaudeAgentOptions(
    setting_sources=["user", "project"],  # Enable filesystem discovery
    project_path=os.getenv("OBSIDIAN_VAULT_PATH")  # Points to Obsidian-Private
)
```

**Expected Outcome**:
- ✅ Auto-discover all 52 personas from `.claude/agents/`
- ✅ Auto-discover all 34 skills from `.claude/skills/`
- ✅ Skills available via `/skills/*` API endpoints
- ✅ Personas available for council consultations

### Phase 10: Council System
The backend already implements:
- `query_persona_with_provider` tool for persona invocation
- Tool-based architecture (no custom parsing needed)
- Multi-LLM support (Anthropic, OpenAI, Google)

**Integration with call-council skill**:
1. User invokes council (via UI or chat message)
2. call-council skill loaded from `.claude/skills/`
3. Skill instructions use `query_persona_with_provider` tool
4. Each persona consulted via their `.claude/agents/*.md` definition
5. Responses synthesized and returned to user

---

## 📋 Action Items for Development Cycle

### Phase 1: Code Review
- [ ] Inventory all 34 skills and categorize them
- [ ] Review persona definitions for consistency
- [ ] Check for any SDK format violations

### Phase 6: SDK Integration
- [ ] Configure SDK auto-discovery for Obsidian-Private
- [ ] Verify all 52 personas load correctly
- [ ] Verify all 34 skills load correctly
- [ ] Test call-council skill with multiple personas

### Phase 7: Documentation
- [ ] Document each persona's purpose and style
- [ ] Document each skill's use case
- [ ] Create persona selection guide
- [ ] Create council best practices guide

---

## 🔍 Discovery Notes

**Why this matters**:
- Previous documentation assumed **5 personas** (Socratic, Contrarian, etc.)
- Reality: **52 personas** already exist in Claude Agent SDK format
- This changes the scope of Phase 10 from "implement personas" to "integrate existing personas"
- SDK auto-discovery (Phase 6) becomes critical for loading all personas

**Implications**:
- No need to create persona system from scratch
- Focus on integration and testing instead
- Leverage existing persona expertise (adam-grant, cal-newport, etc.)
- Rich council consultations possible with 52 different perspectives

---

**Last Updated**: 2026-01-02
**Next Review**: Phase 1 (full skill inventory)
