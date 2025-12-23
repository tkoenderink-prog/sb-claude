"""Sessions API endpoints for session sidebar."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Optional
from datetime import datetime, timedelta, timezone

from core.database import get_db
from models.db_models import ChatSessionDB, ChatMessageDB

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("")
async def list_sessions(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions with preview."""

    # Base query
    query = (
        select(ChatSessionDB)
        .order_by(desc(ChatSessionDB.updated_at))
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    sessions = result.scalars().all()

    # Build response with previews
    session_list = []
    for session in sessions:
        # Get first user message as preview
        preview_result = await db.execute(
            select(ChatMessageDB.content)
            .where(ChatMessageDB.session_id == session.id)
            .where(ChatMessageDB.role == "user")
            .order_by(ChatMessageDB.created_at)
            .limit(1)
        )
        preview = preview_result.scalar_one_or_none()

        # Get message count
        count_result = await db.execute(
            select(func.count(ChatMessageDB.id)).where(
                ChatMessageDB.session_id == session.id
            )
        )
        message_count = count_result.scalar_one()

        session_list.append(
            {
                "id": str(session.id),
                "mode": session.mode,
                "provider": session.provider,
                "model": session.model,
                "title": session.title,
                "preview": (preview[:100] + "...")
                if preview and len(preview) > 100
                else preview,
                "message_count": message_count,
                "created_at": session.created_at.isoformat()
                if session.created_at
                else None,
                "updated_at": session.updated_at.isoformat()
                if session.updated_at
                else None,
            }
        )

    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        session_list = [
            s
            for s in session_list
            if s["preview"] and search_lower in s["preview"].lower()
        ]

    return {
        "sessions": session_list,
        "total": len(session_list),
        "has_more": len(sessions) == limit,
    }


@router.get("/grouped")
async def get_sessions_grouped(
    db: AsyncSession = Depends(get_db),
):
    """Get sessions grouped by time period (Today, Yesterday, This Week, etc.)."""

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    result = await db.execute(
        select(ChatSessionDB).order_by(desc(ChatSessionDB.updated_at)).limit(100)
    )
    sessions = result.scalars().all()

    groups = {
        "today": [],
        "yesterday": [],
        "this_week": [],
        "this_month": [],
        "older": [],
    }

    for session in sessions:
        updated = session.updated_at or session.created_at

        # Get preview
        preview_result = await db.execute(
            select(ChatMessageDB.content)
            .where(ChatMessageDB.session_id == session.id)
            .where(ChatMessageDB.role == "user")
            .order_by(ChatMessageDB.created_at)
            .limit(1)
        )
        preview = preview_result.scalar_one_or_none()

        session_data = {
            "id": str(session.id),
            "title": session.title,
            "preview": (preview[:60] + "...")
            if preview and len(preview) > 60
            else preview,
            "mode": session.mode,
            "updated_at": updated.isoformat() if updated else None,
        }

        if updated >= today_start:
            groups["today"].append(session_data)
        elif updated >= yesterday_start:
            groups["yesterday"].append(session_data)
        elif updated >= week_start:
            groups["this_week"].append(session_data)
        elif updated >= month_start:
            groups["this_month"].append(session_data)
        else:
            groups["older"].append(session_data)

    return groups
