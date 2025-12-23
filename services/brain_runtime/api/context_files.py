"""Context Files API for attaching vault files to chat sessions."""

import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.db_models import ChatContextFileDB, ChatSessionDB


# Load vault path from environment
VAULT_PATH = os.environ.get(
    "OBSIDIAN_VAULT_PATH",
    os.path.expanduser("~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian-Private")
)

# Limits
MAX_CONTEXT_FILES = 10
MAX_CONTEXT_TOKENS = 100_000
TOKENS_PER_CHAR = 0.25  # Rough approximation

router = APIRouter(prefix="/chat/sessions/{session_id}/context", tags=["context-files"])


class ContextFileResponse(BaseModel):
    """Response for a context file."""
    id: str
    file_path: str
    display_name: str
    token_count: int
    content_hash: str
    added_at: datetime


class ContextFilesListResponse(BaseModel):
    """Response for listing context files."""
    files: List[ContextFileResponse]
    total_tokens: int


class AddContextFileRequest(BaseModel):
    """Request to add a context file."""
    file_path: str


def validate_vault_path(file_path: str) -> str:
    """Validate and normalize path within vault. Raises if path escapes vault."""
    # Normalize the path
    full_path = os.path.normpath(os.path.join(VAULT_PATH, file_path))

    # Check it's still within vault
    if not full_path.startswith(os.path.normpath(VAULT_PATH)):
        raise HTTPException(status_code=400, detail="Path must be within vault")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=400, detail="Path must be a file, not a directory")

    return full_path


def estimate_tokens(content: str) -> int:
    """Estimate token count from content length."""
    return int(len(content) * TOKENS_PER_CHAR)


def compute_hash(content: str) -> str:
    """Compute content hash for change detection."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


@router.get("", response_model=ContextFilesListResponse)
async def list_context_files(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all context files attached to a session."""
    # Verify session exists
    session = await db.get(ChatSessionDB, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(ChatContextFileDB)
        .where(ChatContextFileDB.session_id == session_id)
        .order_by(ChatContextFileDB.added_at)
    )
    files = result.scalars().all()

    file_responses = [
        ContextFileResponse(
            id=str(f.id),
            file_path=f.file_path,
            display_name=os.path.basename(f.file_path),
            token_count=f.token_count or 0,
            content_hash=f.content_hash or "",
            added_at=f.added_at,
        )
        for f in files
    ]

    total_tokens = sum(f.token_count for f in file_responses)

    return ContextFilesListResponse(files=file_responses, total_tokens=total_tokens)


@router.post("", response_model=ContextFileResponse)
async def add_context_file(
    session_id: UUID,
    request: AddContextFileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add a vault file to the session context."""
    # Verify session exists
    session = await db.get(ChatSessionDB, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Validate and read file
    full_path = validate_vault_path(request.file_path)

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not a text file")

    token_count = estimate_tokens(content)
    content_hash = compute_hash(content)

    # Check limits
    existing = await db.execute(
        select(ChatContextFileDB)
        .where(ChatContextFileDB.session_id == session_id)
    )
    existing_files = existing.scalars().all()

    # Check for duplicate
    for f in existing_files:
        if f.file_path == request.file_path:
            raise HTTPException(status_code=409, detail="File already attached")

    if len(existing_files) >= MAX_CONTEXT_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_CONTEXT_FILES} context files allowed"
        )

    total_tokens = sum(f.token_count or 0 for f in existing_files) + token_count
    if total_tokens > MAX_CONTEXT_TOKENS:
        raise HTTPException(
            status_code=400,
            detail=f"Total context tokens ({total_tokens}) exceeds limit ({MAX_CONTEXT_TOKENS})"
        )

    # Create context file record
    context_file = ChatContextFileDB(
        session_id=session_id,
        file_path=request.file_path,
        token_count=token_count,
        content_hash=content_hash,
        added_at=datetime.now(timezone.utc),
    )

    db.add(context_file)
    await db.commit()
    await db.refresh(context_file)

    return ContextFileResponse(
        id=str(context_file.id),
        file_path=context_file.file_path,
        display_name=os.path.basename(context_file.file_path),
        token_count=context_file.token_count or 0,
        content_hash=context_file.content_hash or "",
        added_at=context_file.added_at,
    )


@router.delete("/{file_id}")
async def remove_context_file(
    session_id: UUID,
    file_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a file from the session context."""
    result = await db.execute(
        select(ChatContextFileDB)
        .where(
            ChatContextFileDB.id == file_id,
            ChatContextFileDB.session_id == session_id,
        )
    )
    context_file = result.scalar_one_or_none()

    if not context_file:
        raise HTTPException(status_code=404, detail="Context file not found")

    await db.delete(context_file)
    await db.commit()

    return {"message": "File removed from context"}


# Vault browsing endpoints
vault_router = APIRouter(prefix="/vault", tags=["vault"])


class VaultFile(BaseModel):
    """A file or directory in the vault."""
    name: str
    path: str
    is_directory: bool
    size: Optional[int] = None


class VaultBrowseResponse(BaseModel):
    """Response for browsing vault."""
    current_path: str
    parent_path: Optional[str]
    items: List[VaultFile]


@vault_router.get("/browse", response_model=VaultBrowseResponse)
async def browse_vault(
    path: str = Query("", description="Path relative to vault root"),
):
    """Browse vault directory structure."""
    # Normalize and validate path
    if path:
        full_path = os.path.normpath(os.path.join(VAULT_PATH, path))
        if not full_path.startswith(os.path.normpath(VAULT_PATH)):
            raise HTTPException(status_code=400, detail="Path must be within vault")
    else:
        full_path = VAULT_PATH
        path = ""

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Path not found")

    if not os.path.isdir(full_path):
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    try:
        for entry in sorted(os.listdir(full_path)):
            # Skip hidden files and directories
            if entry.startswith('.'):
                continue

            entry_path = os.path.join(full_path, entry)
            relative_path = os.path.join(path, entry) if path else entry

            is_dir = os.path.isdir(entry_path)
            size = None if is_dir else os.path.getsize(entry_path)

            # Only show markdown files and directories
            if is_dir or entry.endswith('.md'):
                items.append(VaultFile(
                    name=entry,
                    path=relative_path,
                    is_directory=is_dir,
                    size=size,
                ))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Compute parent path
    parent_path = os.path.dirname(path) if path else None

    return VaultBrowseResponse(
        current_path=path,
        parent_path=parent_path,
        items=items,
    )


class VaultSearchResult(BaseModel):
    """A search result from the vault."""
    name: str
    path: str
    size: int


@vault_router.get("/search-files")
async def search_vault_files(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search vault files by name."""
    query_lower = query.lower()
    results = []

    for root, dirs, files in os.walk(VAULT_PATH):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for filename in files:
            if not filename.endswith('.md'):
                continue
            if query_lower not in filename.lower():
                continue

            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, VAULT_PATH)

            results.append(VaultSearchResult(
                name=filename,
                path=relative_path,
                size=os.path.getsize(full_path),
            ))

            if len(results) >= limit:
                break

        if len(results) >= limit:
            break

    return {"results": results, "query": query}
