"""Health check endpoint."""

import os
from fastapi import APIRouter
from core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status, version, and environment info
    """
    settings = get_settings()

    # Determine if running in container
    in_container = os.path.exists("/.dockerenv") or os.environ.get("container") == "docker"

    return {
        "status": "ok",
        "version": settings.version,
        "service": settings.service_name,
        "environment": {
            "mode": settings.dev_mode,
            "port": settings.dev_port,
            "in_container": in_container,
            "chroma_host": settings.chroma_host,
            "chroma_port": settings.chroma_port,
        },
    }
