"""API routes for the Brain Runtime service."""

from .health import router as health_router
from .jobs import router as jobs_router
from .processors import router as processors_router
from .calendar import router as calendar_router
from .tasks import router as tasks_router
from .vault import router as vault_router
from .skills import router as skills_router
from .agent import router as agent_router
from .chat import router as chat_router
from .sessions import router as sessions_router
from .proposals import router as proposals_router
from .settings import router as settings_router
# Phase 9 routers
from .search import router as search_router
from .sync import router as sync_router
from .modes import router as modes_router
from .modes import commands_router
from .context_files import router as context_files_router
from .context_files import vault_router as vault_browse_router
# Phase 10 routers
from .personas import router as personas_router
from .councils import router as councils_router

__all__ = [
    "health_router",
    "jobs_router",
    "processors_router",
    "calendar_router",
    "tasks_router",
    "vault_router",
    "skills_router",
    "agent_router",
    "chat_router",
    "sessions_router",
    "proposals_router",
    "settings_router",
    # Phase 9
    "search_router",
    "sync_router",
    "modes_router",
    "commands_router",
    "context_files_router",
    "vault_browse_router",
    # Phase 10
    "personas_router",
    "councils_router",
]
