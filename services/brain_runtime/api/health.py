"""Health check endpoint."""

from fastapi import APIRouter
from core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service health status and version
    """
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.version,
        "service": settings.service_name,
    }
