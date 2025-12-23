"""Modes API endpoints for Phase 9 - Custom conversation modes and commands."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.db_models import ModeDB, StandardCommandDB

router = APIRouter(prefix="/modes", tags=["modes"])


# ============================================================================
# Pydantic Models
# ============================================================================


class CommandResponse(BaseModel):
    """Response for a command."""

    id: str
    mode_id: Optional[str]
    name: str
    description: Optional[str]
    prompt: str
    icon: Optional[str]
    sort_order: int


class ModeResponse(BaseModel):
    """Response for a mode."""

    id: str
    name: str
    description: Optional[str]
    icon: str
    color: str
    system_prompt_addition: Optional[str]
    default_model: Optional[str]
    sort_order: int
    is_default: bool
    is_system: bool
    commands: List[CommandResponse] = []


class CreateModeRequest(BaseModel):
    """Request to create a mode."""

    name: str
    description: Optional[str] = None
    icon: str = "?"
    color: str = "#3B82F6"
    system_prompt_addition: Optional[str] = None
    default_model: Optional[str] = None
    sort_order: int = 0
    is_default: bool = False


class UpdateModeRequest(BaseModel):
    """Request to update a mode."""

    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    system_prompt_addition: Optional[str] = None
    default_model: Optional[str] = None
    sort_order: Optional[int] = None
    is_default: Optional[bool] = None


class CreateCommandRequest(BaseModel):
    """Request to create a command."""

    mode_id: Optional[str] = None  # NULL = global
    name: str
    description: Optional[str] = None
    prompt: str
    icon: Optional[str] = None
    sort_order: int = 0


class UpdateCommandRequest(BaseModel):
    """Request to update a command."""

    name: Optional[str] = None
    description: Optional[str] = None
    prompt: Optional[str] = None
    icon: Optional[str] = None
    sort_order: Optional[int] = None


# ============================================================================
# Mode Endpoints
# ============================================================================


@router.get("", response_model=List[ModeResponse])
async def list_modes(
    include_deleted: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all modes with their associated commands."""
    query = select(ModeDB).order_by(ModeDB.sort_order, ModeDB.name)
    if not include_deleted:
        query = query.where(ModeDB.deleted_at.is_(None))

    result = await db.execute(query)
    modes = result.scalars().all()

    # Get commands for each mode
    response = []
    for mode in modes:
        # Get mode-specific commands
        cmd_query = select(StandardCommandDB).where(
            StandardCommandDB.mode_id == mode.id,
            StandardCommandDB.deleted_at.is_(None),
        ).order_by(StandardCommandDB.sort_order)
        cmd_result = await db.execute(cmd_query)
        commands = cmd_result.scalars().all()

        response.append(
            ModeResponse(
                id=str(mode.id),
                name=mode.name,
                description=mode.description,
                icon=mode.icon or "?",
                color=mode.color or "#3B82F6",
                system_prompt_addition=mode.system_prompt_addition,
                default_model=mode.default_model,
                sort_order=mode.sort_order or 0,
                is_default=mode.is_default or False,
                is_system=mode.is_system or False,
                commands=[
                    CommandResponse(
                        id=str(c.id),
                        mode_id=str(c.mode_id) if c.mode_id else None,
                        name=c.name,
                        description=c.description,
                        prompt=c.prompt,
                        icon=c.icon,
                        sort_order=c.sort_order or 0,
                    )
                    for c in commands
                ],
            )
        )

    return response


@router.get("/{mode_id}", response_model=ModeResponse)
async def get_mode(mode_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific mode with its commands."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == UUID(mode_id),
            ModeDB.deleted_at.is_(None),
        )
    )
    mode = result.scalar_one_or_none()

    if not mode:
        raise HTTPException(status_code=404, detail="Mode not found")

    # Get commands
    cmd_result = await db.execute(
        select(StandardCommandDB).where(
            StandardCommandDB.mode_id == mode.id,
            StandardCommandDB.deleted_at.is_(None),
        ).order_by(StandardCommandDB.sort_order)
    )
    commands = cmd_result.scalars().all()

    return ModeResponse(
        id=str(mode.id),
        name=mode.name,
        description=mode.description,
        icon=mode.icon or "?",
        color=mode.color or "#3B82F6",
        system_prompt_addition=mode.system_prompt_addition,
        default_model=mode.default_model,
        sort_order=mode.sort_order or 0,
        is_default=mode.is_default or False,
        is_system=mode.is_system or False,
        commands=[
            CommandResponse(
                id=str(c.id),
                mode_id=str(c.mode_id) if c.mode_id else None,
                name=c.name,
                description=c.description,
                prompt=c.prompt,
                icon=c.icon,
                sort_order=c.sort_order or 0,
            )
            for c in commands
        ],
    )


@router.post("", response_model=ModeResponse)
async def create_mode(request: CreateModeRequest, db: AsyncSession = Depends(get_db)):
    """Create a new custom mode."""
    # If setting as default, unset other defaults
    if request.is_default:
        await db.execute(
            update(ModeDB)
            .where(ModeDB.deleted_at.is_(None))
            .values(is_default=False)
        )

    mode = ModeDB(
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color,
        system_prompt_addition=request.system_prompt_addition,
        default_model=request.default_model,
        sort_order=request.sort_order,
        is_default=request.is_default,
        is_system=False,
    )
    db.add(mode)
    await db.commit()
    await db.refresh(mode)

    return ModeResponse(
        id=str(mode.id),
        name=mode.name,
        description=mode.description,
        icon=mode.icon or "?",
        color=mode.color or "#3B82F6",
        system_prompt_addition=mode.system_prompt_addition,
        default_model=mode.default_model,
        sort_order=mode.sort_order or 0,
        is_default=mode.is_default or False,
        is_system=mode.is_system or False,
        commands=[],
    )


@router.patch("/{mode_id}", response_model=ModeResponse)
async def update_mode(
    mode_id: str,
    request: UpdateModeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a mode."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == UUID(mode_id),
            ModeDB.deleted_at.is_(None),
        )
    )
    mode = result.scalar_one_or_none()

    if not mode:
        raise HTTPException(status_code=404, detail="Mode not found")

    # Don't allow editing system modes (except sort_order and is_default)
    if mode.is_system:
        allowed_fields = {"sort_order", "is_default"}
        update_data = request.model_dump(exclude_unset=True)
        disallowed = set(update_data.keys()) - allowed_fields
        if disallowed:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot modify system mode fields: {disallowed}",
            )

    # If setting as default, unset other defaults
    if request.is_default:
        await db.execute(
            update(ModeDB)
            .where(ModeDB.id != UUID(mode_id), ModeDB.deleted_at.is_(None))
            .values(is_default=False)
        )

    # Update fields
    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(mode, key, value)

    await db.commit()
    await db.refresh(mode)

    # Get commands
    cmd_result = await db.execute(
        select(StandardCommandDB).where(
            StandardCommandDB.mode_id == mode.id,
            StandardCommandDB.deleted_at.is_(None),
        ).order_by(StandardCommandDB.sort_order)
    )
    commands = cmd_result.scalars().all()

    return ModeResponse(
        id=str(mode.id),
        name=mode.name,
        description=mode.description,
        icon=mode.icon or "?",
        color=mode.color or "#3B82F6",
        system_prompt_addition=mode.system_prompt_addition,
        default_model=mode.default_model,
        sort_order=mode.sort_order or 0,
        is_default=mode.is_default or False,
        is_system=mode.is_system or False,
        commands=[
            CommandResponse(
                id=str(c.id),
                mode_id=str(c.mode_id) if c.mode_id else None,
                name=c.name,
                description=c.description,
                prompt=c.prompt,
                icon=c.icon,
                sort_order=c.sort_order or 0,
            )
            for c in commands
        ],
    )


@router.delete("/{mode_id}")
async def delete_mode(mode_id: str, db: AsyncSession = Depends(get_db)):
    """Soft delete a mode."""
    result = await db.execute(
        select(ModeDB).where(
            ModeDB.id == UUID(mode_id),
            ModeDB.deleted_at.is_(None),
        )
    )
    mode = result.scalar_one_or_none()

    if not mode:
        raise HTTPException(status_code=404, detail="Mode not found")

    if mode.is_system:
        raise HTTPException(status_code=403, detail="Cannot delete system modes")

    mode.deleted_at = datetime.utcnow()
    await db.commit()

    return {"message": "Mode deleted", "id": mode_id}


# ============================================================================
# Command Endpoints
# ============================================================================

commands_router = APIRouter(prefix="/commands", tags=["commands"])


@commands_router.get("", response_model=List[CommandResponse])
async def list_commands(
    mode_id: Optional[str] = None,
    global_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List commands. Filter by mode_id or get global commands only."""
    query = select(StandardCommandDB).where(
        StandardCommandDB.deleted_at.is_(None)
    ).order_by(StandardCommandDB.sort_order)

    if global_only:
        query = query.where(StandardCommandDB.mode_id.is_(None))
    elif mode_id:
        query = query.where(StandardCommandDB.mode_id == UUID(mode_id))

    result = await db.execute(query)
    commands = result.scalars().all()

    return [
        CommandResponse(
            id=str(c.id),
            mode_id=str(c.mode_id) if c.mode_id else None,
            name=c.name,
            description=c.description,
            prompt=c.prompt,
            icon=c.icon,
            sort_order=c.sort_order or 0,
        )
        for c in commands
    ]


@commands_router.post("", response_model=CommandResponse)
async def create_command(
    request: CreateCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new command."""
    command = StandardCommandDB(
        mode_id=UUID(request.mode_id) if request.mode_id else None,
        name=request.name,
        description=request.description,
        prompt=request.prompt,
        icon=request.icon,
        sort_order=request.sort_order,
    )
    db.add(command)
    await db.commit()
    await db.refresh(command)

    return CommandResponse(
        id=str(command.id),
        mode_id=str(command.mode_id) if command.mode_id else None,
        name=command.name,
        description=command.description,
        prompt=command.prompt,
        icon=command.icon,
        sort_order=command.sort_order or 0,
    )


@commands_router.patch("/{command_id}", response_model=CommandResponse)
async def update_command(
    command_id: str,
    request: UpdateCommandRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update a command."""
    result = await db.execute(
        select(StandardCommandDB).where(
            StandardCommandDB.id == UUID(command_id),
            StandardCommandDB.deleted_at.is_(None),
        )
    )
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(command, key, value)

    await db.commit()
    await db.refresh(command)

    return CommandResponse(
        id=str(command.id),
        mode_id=str(command.mode_id) if command.mode_id else None,
        name=command.name,
        description=command.description,
        prompt=command.prompt,
        icon=command.icon,
        sort_order=command.sort_order or 0,
    )


@commands_router.delete("/{command_id}")
async def delete_command(command_id: str, db: AsyncSession = Depends(get_db)):
    """Soft delete a command."""
    result = await db.execute(
        select(StandardCommandDB).where(
            StandardCommandDB.id == UUID(command_id),
            StandardCommandDB.deleted_at.is_(None),
        )
    )
    command = result.scalar_one_or_none()

    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    command.deleted_at = datetime.utcnow()
    await db.commit()

    return {"message": "Command deleted", "id": command_id}
