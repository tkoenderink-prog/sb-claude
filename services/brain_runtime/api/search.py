"""Search API endpoints for Phase 9 - Conversation Search."""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db

router = APIRouter(prefix="/search", tags=["search"])


class ConversationSearchResult(BaseModel):
    """Search result for a conversation."""

    session_id: str
    title: Optional[str]
    created_at: datetime
    snippet: str  # Highlighted match
    message_count: int
    rank: float


class ConversationSearchResponse(BaseModel):
    """Response for conversation search."""

    results: List[ConversationSearchResult]
    total: int
    query: str


@router.get("/conversations", response_model=ConversationSearchResponse)
async def search_conversations(
    query: str = Query(..., min_length=1, description="Search query"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """Search conversations using full-text search.

    Uses PostgreSQL's built-in full-text search with ts_headline for snippets.
    plainto_tsquery() sanitizes input, preventing SQL injection.
    """
    # Build dynamic WHERE clause to avoid NULL parameter type issues
    where_clauses = ["m.search_vector @@ plainto_tsquery('english', :query)"]
    params: dict = {"query": query, "limit": limit}

    if start_date is not None:
        where_clauses.append("s.created_at >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        where_clauses.append("s.created_at <= :end_date")
        params["end_date"] = end_date

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT * FROM (
        SELECT DISTINCT ON (s.id)
            s.id,
            s.title,
            s.created_at,
            ts_headline('english', m.content, plainto_tsquery('english', :query),
                'MaxWords=30, MinWords=15, StartSel=<mark>, StopSel=</mark>') as snippet,
            ts_rank(m.search_vector, plainto_tsquery('english', :query)) as rank,
            (SELECT COUNT(*) FROM chat_messages WHERE session_id = s.id) as message_count
        FROM chat_sessions s
        JOIN chat_messages m ON m.session_id = s.id
        WHERE {where_sql}
        ORDER BY s.id, rank DESC, m.created_at DESC
    ) AS unique_sessions
    ORDER BY rank DESC, created_at DESC
    LIMIT :limit
    """

    result = await db.execute(text(sql), params)

    rows = result.fetchall()

    results = [
        ConversationSearchResult(
            session_id=str(row.id),
            title=row.title,
            created_at=row.created_at,
            snippet=row.snippet or "",
            message_count=row.message_count or 0,
            rank=float(row.rank) if row.rank else 0.0,
        )
        for row in rows
    ]

    return ConversationSearchResponse(
        results=results,
        total=len(results),
        query=query,
    )


class MessageSearchResult(BaseModel):
    """Search result for an individual message."""

    message_id: str
    session_id: str
    session_title: Optional[str]
    role: str
    snippet: str
    created_at: datetime
    rank: float


@router.get("/messages")
async def search_messages(
    query: str = Query(..., min_length=1, description="Search query"),
    session_id: Optional[str] = Query(None, description="Filter by session"),
    role: Optional[str] = Query(None, description="Filter by role (user/assistant)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    db: AsyncSession = Depends(get_db),
):
    """Search individual messages across all conversations."""
    # Build dynamic WHERE clause to avoid NULL parameter type issues
    where_clauses = ["m.search_vector @@ plainto_tsquery('english', :query)"]
    params: dict = {"query": query, "limit": limit}

    if session_id is not None:
        where_clauses.append("m.session_id = :session_id::uuid")
        params["session_id"] = session_id
    if role is not None:
        where_clauses.append("m.role = :role")
        params["role"] = role

    where_sql = " AND ".join(where_clauses)

    sql = f"""
    SELECT
        m.id as message_id,
        m.session_id,
        s.title as session_title,
        m.role,
        ts_headline('english', m.content, plainto_tsquery('english', :query),
            'MaxWords=50, MinWords=25, StartSel=<mark>, StopSel=</mark>') as snippet,
        m.created_at,
        ts_rank(m.search_vector, plainto_tsquery('english', :query)) as rank
    FROM chat_messages m
    JOIN chat_sessions s ON s.id = m.session_id
    WHERE {where_sql}
    ORDER BY rank DESC, m.created_at DESC
    LIMIT :limit
    """

    result = await db.execute(text(sql), params)

    rows = result.fetchall()

    return {
        "results": [
            MessageSearchResult(
                message_id=str(row.message_id),
                session_id=str(row.session_id),
                session_title=row.session_title,
                role=row.role,
                snippet=row.snippet or "",
                created_at=row.created_at,
                rank=float(row.rank) if row.rank else 0.0,
            )
            for row in rows
        ],
        "total": len(rows),
        "query": query,
    }
