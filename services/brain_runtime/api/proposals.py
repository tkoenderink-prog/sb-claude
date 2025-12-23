"""Proposal API endpoints for file change proposals."""

import logging
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.proposal_service import (
    ProposalService,
    ProposalError,
)
from models.db_models import ProposalDB, ProposalFileDB

router = APIRouter(prefix="/proposals", tags=["proposals"])
logger = logging.getLogger(__name__)


class ProposalFileResponse(BaseModel):
    """Response model for proposal file."""
    id: str
    proposal_id: str
    file_path: str
    operation: str
    original_content: Optional[str] = None
    proposed_content: Optional[str] = None
    diff_hunks: Optional[List[dict]] = None


class ProposalResponse(BaseModel):
    """Response model for proposal."""
    id: str
    session_id: str
    status: str
    description: str
    created_at: Optional[str] = None
    applied_at: Optional[str] = None
    backup_path: Optional[str] = None
    files: Optional[List[ProposalFileResponse]] = None


class CreateProposalRequest(BaseModel):
    """Request model for creating a proposal."""
    session_id: str
    description: str
    files: List[dict]  # [{file_path, operation, content}]


@router.get("")
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List proposals with optional status filter."""
    query = select(ProposalDB).order_by(ProposalDB.created_at.desc()).limit(limit)

    if status:
        query = query.where(ProposalDB.status == status)

    result = await db.execute(query)
    proposals = result.scalars().all()

    return {
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals),
    }


@router.get("/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get proposal with files and diffs."""
    # Get proposal
    result = await db.execute(
        select(ProposalDB).where(ProposalDB.id == uuid.UUID(proposal_id))
    )
    proposal = result.scalar_one_or_none()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Get files
    files_result = await db.execute(
        select(ProposalFileDB).where(
            ProposalFileDB.proposal_id == uuid.UUID(proposal_id)
        )
    )
    files = files_result.scalars().all()

    response = proposal.to_dict()
    response["files"] = [f.to_dict() for f in files]

    return response


@router.post("")
async def create_proposal(
    request: CreateProposalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new proposal with files."""
    service = ProposalService(db)

    try:
        # Create proposal
        proposal = await service.create_proposal(
            session_id=request.session_id,
            description=request.description,
        )

        # Add files
        for file_data in request.files:
            await service.add_file_change(
                proposal_id=str(proposal.id),
                file_path=file_data["file_path"],
                operation=file_data["operation"],
                new_content=file_data.get("content"),
            )

        await db.commit()

        # Return proposal with files
        files = await service.get_proposal_files(str(proposal.id))
        response = proposal.to_dict()
        response["files"] = [f.to_dict() for f in files]

        return response

    except ProposalError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to create proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Approve and apply a proposal."""
    service = ProposalService(db)

    try:
        # Mark as approved
        await service.approve_proposal(proposal_id)

        # Apply changes with git integration (auto-commit before/after)
        proposal = await service.apply_proposal_with_git(proposal_id)
        await db.commit()

        return {
            "status": "applied",
            "proposal": proposal.to_dict(),
            "message": "Proposal applied successfully",
        }

    except ProposalError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to approve proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposal."""
    service = ProposalService(db)

    try:
        proposal = await service.reject_proposal(proposal_id)
        await db.commit()

        return {
            "status": "rejected",
            "proposal": proposal.to_dict(),
            "message": "Proposal rejected",
        }

    except ProposalError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to reject proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
