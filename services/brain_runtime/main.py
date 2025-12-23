"""FastAPI application for the Brain Runtime service."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

from core.config import get_settings
from core.database import init_db
from core.tools import register_all_tools
from core.errors import AppError, app_error_handler
from api import (
    health_router,
    jobs_router,
    processors_router,
    calendar_router,
    tasks_router,
    vault_router,
    skills_router,
    chat_router,
    agent_router,
    sessions_router,
    proposals_router,
    settings_router,
    # Phase 9
    search_router,
    sync_router,
    modes_router,
    commands_router,
    context_files_router,
    vault_browse_router,
    # Phase 10
    personas_router,
    councils_router,
)
from api.sync import reset_stuck_syncs

logger = logging.getLogger(__name__)

# Load environment variables from ../../.env
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(name)s - %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting brain-runtime...")

    # Initialize database connection pool
    await init_db()
    logger.info("Database initialized")

    # Reset any syncs stuck in 'running' state from previous server instance
    await reset_stuck_syncs()

    # Register all tools
    tool_count = register_all_tools()
    logger.info(f"Tool registry initialized with {tool_count} tools")

    yield

    # Shutdown
    logger.info("Shutting down brain-runtime...")


# Create FastAPI app
app = FastAPI(
    title="Second Brain Runtime",
    description="Backend service for AI Second Brain System",
    version=settings.version,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
app.add_exception_handler(AppError, app_error_handler)

# Register routers
app.include_router(health_router)
app.include_router(jobs_router)
app.include_router(processors_router)
app.include_router(calendar_router)
app.include_router(tasks_router)
app.include_router(vault_router)
app.include_router(skills_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(sessions_router)
app.include_router(proposals_router)
app.include_router(settings_router)
# Phase 9 routers
app.include_router(search_router)
app.include_router(sync_router)
app.include_router(modes_router)
app.include_router(commands_router)
app.include_router(context_files_router)
app.include_router(vault_browse_router)
# Phase 10 routers
app.include_router(personas_router)
app.include_router(councils_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": settings.version,
        "status": "running",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
