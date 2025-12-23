"""Settings API endpoints for user settings and API key management."""

import logging
import os
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.proposal_service import get_or_create_settings
from core.encryption import encrypt_api_key, decrypt_api_key, get_key_suffix
from models.db_models import ApiKeyDB

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


# ============================================================================
# Settings Models
# ============================================================================


class SettingsResponse(BaseModel):
    """Response model for settings."""
    id: str
    yolo_mode: bool
    default_model: str
    system_prompt: Optional[str]
    system_prompt_history: List[dict]


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""
    yolo_mode: Optional[bool] = None
    default_model: Optional[str] = None
    system_prompt: Optional[str] = None


class SystemPromptHistoryEntry(BaseModel):
    """Entry in system prompt history."""
    content: str
    saved_at: str


# ============================================================================
# Settings Endpoints
# ============================================================================


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
):
    """Get user settings."""
    settings = await get_or_create_settings(db)
    return settings.to_dict()


@router.patch("")
async def update_settings(
    request: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    settings = await get_or_create_settings(db)

    if request.yolo_mode is not None:
        settings.yolo_mode = request.yolo_mode
        logger.info(f"YOLO mode set to: {request.yolo_mode}")

    if request.default_model is not None:
        settings.default_model = request.default_model
        logger.info(f"Default model set to: {request.default_model}")

    if request.system_prompt is not None:
        # Save current prompt to history before updating
        history = settings.system_prompt_history or []
        if settings.system_prompt:  # Only add to history if there was a previous prompt
            entry = {
                "content": settings.system_prompt,
                "saved_at": datetime.utcnow().isoformat(),
            }
            history = [entry] + history
            history = history[:5]  # Keep only last 5
        settings.system_prompt_history = history
        settings.system_prompt = request.system_prompt
        logger.info("System prompt updated")

    await db.commit()
    await db.refresh(settings)

    return settings.to_dict()


@router.get("/system-prompt/history")
async def get_system_prompt_history(
    db: AsyncSession = Depends(get_db),
):
    """Get system prompt version history."""
    settings = await get_or_create_settings(db)
    return {
        "current": settings.system_prompt,
        "history": settings.system_prompt_history or [],
    }


@router.post("/system-prompt/restore/{index}")
async def restore_system_prompt(
    index: int,
    db: AsyncSession = Depends(get_db),
):
    """Restore a previous system prompt from history."""
    settings = await get_or_create_settings(db)
    history = settings.system_prompt_history or []

    if index < 0 or index >= len(history):
        raise HTTPException(status_code=400, detail="Invalid history index")

    # Save current to history
    if settings.system_prompt:
        entry = {
            "content": settings.system_prompt,
            "saved_at": datetime.utcnow().isoformat(),
        }
        history = [entry] + history
        history = history[:5]

    # Restore from history
    restored = history[index]["content"]
    settings.system_prompt = restored
    settings.system_prompt_history = history

    await db.commit()
    await db.refresh(settings)

    return settings.to_dict()


# ============================================================================
# API Key Models
# ============================================================================


class ApiKeyResponse(BaseModel):
    """Response for an API key (never includes full key)."""
    provider: str
    key_suffix: Optional[str]
    is_valid: bool
    last_validated: Optional[datetime]
    source: str  # 'database' or 'environment'


class ApiKeyListResponse(BaseModel):
    """Response for listing API keys."""
    keys: List[ApiKeyResponse]


class ApiKeyCreateRequest(BaseModel):
    """Request to create/update an API key."""
    key: str


class ApiKeyTestResponse(BaseModel):
    """Response for testing an API key."""
    valid: bool
    message: str


# ============================================================================
# API Key Endpoints
# ============================================================================

# Supported providers and their environment variable names
PROVIDERS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
}


@router.get("/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(db: AsyncSession = Depends(get_db)):
    """List all API keys (suffixes only, never full keys)."""
    result = await db.execute(select(ApiKeyDB))
    db_keys = {k.provider: k for k in result.scalars().all()}

    keys = []
    for provider, env_var in PROVIDERS.items():
        if provider in db_keys:
            db_key = db_keys[provider]
            keys.append(
                ApiKeyResponse(
                    provider=provider,
                    key_suffix=db_key.key_suffix,
                    is_valid=db_key.is_valid,
                    last_validated=db_key.last_validated,
                    source="database",
                )
            )
        elif os.getenv(env_var):
            # Key exists in environment
            env_key = os.getenv(env_var)
            keys.append(
                ApiKeyResponse(
                    provider=provider,
                    key_suffix=get_key_suffix(env_key) if env_key else None,
                    is_valid=True,  # Assume env keys are valid
                    last_validated=None,
                    source="environment",
                )
            )
        else:
            # No key configured
            keys.append(
                ApiKeyResponse(
                    provider=provider,
                    key_suffix=None,
                    is_valid=False,
                    last_validated=None,
                    source="none",
                )
            )

    return ApiKeyListResponse(keys=keys)


@router.put("/api-keys/{provider}")
async def update_api_key(
    provider: str,
    request: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or update an API key for a provider."""
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {list(PROVIDERS.keys())}",
        )

    # Check if key already exists
    result = await db.execute(
        select(ApiKeyDB).where(ApiKeyDB.provider == provider)
    )
    existing = result.scalar_one_or_none()

    encrypted = encrypt_api_key(request.key)
    suffix = get_key_suffix(request.key)

    if existing:
        existing.encrypted_key = encrypted
        existing.key_suffix = suffix
        existing.is_valid = True  # Reset validation status
        existing.last_validated = None
    else:
        new_key = ApiKeyDB(
            provider=provider,
            encrypted_key=encrypted,
            key_suffix=suffix,
            is_valid=True,
        )
        db.add(new_key)

    await db.commit()

    return {"message": f"API key for {provider} updated", "provider": provider}


@router.delete("/api-keys/{provider}")
async def delete_api_key(provider: str, db: AsyncSession = Depends(get_db)):
    """Delete an API key for a provider."""
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {list(PROVIDERS.keys())}",
        )

    await db.execute(delete(ApiKeyDB).where(ApiKeyDB.provider == provider))
    await db.commit()

    return {"message": f"API key for {provider} deleted", "provider": provider}


@router.post("/api-keys/{provider}/test", response_model=ApiKeyTestResponse)
async def test_api_key(provider: str, db: AsyncSession = Depends(get_db)):
    """Test if an API key is valid."""
    if provider not in PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider. Must be one of: {list(PROVIDERS.keys())}",
        )

    # Get key from database or environment
    result = await db.execute(
        select(ApiKeyDB).where(ApiKeyDB.provider == provider)
    )
    db_key = result.scalar_one_or_none()

    if db_key:
        api_key = decrypt_api_key(db_key.encrypted_key)
    else:
        env_var = PROVIDERS[provider]
        api_key = os.getenv(env_var)

    if not api_key:
        return ApiKeyTestResponse(valid=False, message="No API key configured")

    # Test the key based on provider
    try:
        if provider == "anthropic":
            valid = await _test_anthropic_key(api_key)
        elif provider == "openai":
            valid = await _test_openai_key(api_key)
        else:
            valid = True  # Skip validation for unsupported providers

        # Update validation status in database
        if db_key:
            db_key.is_valid = valid
            db_key.last_validated = datetime.utcnow()
            await db.commit()

        return ApiKeyTestResponse(
            valid=valid,
            message="API key is valid" if valid else "API key is invalid",
        )
    except Exception as e:
        logger.error(f"Error testing {provider} key: {e}")
        return ApiKeyTestResponse(valid=False, message=f"Error testing key: {str(e)}")


async def _test_anthropic_key(api_key: str) -> bool:
    """Test Anthropic API key with minimal request."""
    try:
        from anthropic import Anthropic, AuthenticationError

        client = Anthropic(api_key=api_key)
        # Minimal request to validate
        client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True
    except AuthenticationError:
        return False
    except Exception as e:
        logger.error(f"Anthropic key test error: {e}")
        return False


async def _test_openai_key(api_key: str) -> bool:
    """Test OpenAI API key with minimal request."""
    try:
        from openai import OpenAI, AuthenticationError

        client = OpenAI(api_key=api_key)
        # Minimal request to validate
        client.models.list()
        return True
    except AuthenticationError:
        return False
    except Exception as e:
        logger.error(f"OpenAI key test error: {e}")
        return False


# ============================================================================
# API Key Resolution (for use by other modules)
# ============================================================================


async def get_api_key(provider: str, db: AsyncSession) -> str:
    """Get API key with priority: DB > env > error.

    Used by chat and other modules that need API keys.
    """
    # Try database first
    result = await db.execute(
        select(ApiKeyDB).where(ApiKeyDB.provider == provider)
    )
    db_key = result.scalar_one_or_none()

    if db_key:
        return decrypt_api_key(db_key.encrypted_key)

    # Fallback to environment
    env_var = PROVIDERS.get(provider, f"{provider.upper()}_API_KEY")
    env_key = os.getenv(env_var)
    if env_key:
        return env_key

    raise HTTPException(
        status_code=500,
        detail=f"No API key configured for {provider}",
    )
