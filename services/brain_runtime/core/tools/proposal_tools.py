"""Proposal tools for LLM to create file change proposals."""

import logging
import uuid
from typing import Optional

from .registry import tool
from core.proposal_service import (
    ProposalService,
    ProposalError,
    get_or_create_settings,
)
from core.database import get_session

logger = logging.getLogger(__name__)


def _validate_or_generate_session_id(session_id: Optional[str]) -> str:
    """Validate session_id is a valid UUID or generate a new one."""
    if session_id:
        try:
            # Try to parse as UUID to validate
            uuid.UUID(session_id)
            return session_id
        except ValueError:
            logger.warning(f"Invalid session_id '{session_id}', generating new UUID")
    return str(uuid.uuid4())


@tool(
    name="propose_file_change",
    description="Propose changes to an existing file in the vault. The user will see a diff and can approve or reject.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Vault-relative path to the file (e.g., 'Notes/Daily/2025-12-21.md')",
            },
            "new_content": {
                "type": "string",
                "description": "Complete new content for the file. Must include the entire file, not just changes.",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of what changes are being made and why.",
            },
            "session_id": {
                "type": "string",
                "description": "The chat session ID for this proposal.",
            },
        },
        "required": ["file_path", "new_content", "description", "session_id"],
    },
)
async def propose_file_change(
    file_path: str,
    new_content: str,
    description: str,
    session_id: str,
):
    """Create a proposal to modify an existing file."""
    validated_session_id = _validate_or_generate_session_id(session_id)

    async with get_session() as db:
        service = ProposalService(db)

        try:
            # Create proposal
            proposal = await service.create_proposal(
                session_id=validated_session_id,
                description=description,
            )

            # Add file change
            proposal_file = await service.add_file_change(
                proposal_id=str(proposal.id),
                file_path=file_path,
                operation="modify",
                new_content=new_content,
            )

            # Check YOLO mode
            settings = await get_or_create_settings(db)
            auto_applied = False

            if settings.yolo_mode:
                # Auto-apply for modifies (not deletes)
                await service.apply_proposal(str(proposal.id))
                auto_applied = True
                status = "applied"
            else:
                status = "pending"

            await db.commit()

            # Calculate diff stats
            lines_added = 0
            lines_removed = 0
            if proposal_file.diff_hunks:
                for hunk in proposal_file.diff_hunks:
                    for line in hunk.get("lines", []):
                        if line.startswith("+") and not line.startswith("+++"):
                            lines_added += 1
                        elif line.startswith("-") and not line.startswith("---"):
                            lines_removed += 1

            # Generate diff preview
            diff_preview = ""
            if proposal_file.diff_hunks:
                all_lines = []
                for hunk in proposal_file.diff_hunks[:2]:  # First 2 hunks
                    all_lines.extend(hunk.get("lines", [])[:10])  # First 10 lines each
                diff_preview = "\n".join(all_lines)[:500]

            return {
                "proposal_id": str(proposal.id),
                "status": status,
                "auto_applied": auto_applied,
                "diff_preview": diff_preview,
                "lines_added": lines_added,
                "lines_removed": lines_removed,
                "message": "Changes applied automatically" if auto_applied else "Proposal created. User can view diff and approve.",
            }

        except ProposalError as e:
            logger.error(f"Proposal error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating proposal: {e}")
            return {"error": str(e)}


@tool(
    name="propose_new_file",
    description="Propose creating a new file in the vault. The user will see the content and can approve or reject.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Vault-relative path for the new file (e.g., 'Notes/Ideas/new-idea.md')",
            },
            "content": {
                "type": "string",
                "description": "Content for the new file.",
            },
            "description": {
                "type": "string",
                "description": "Human-readable description of what this file is for.",
            },
            "session_id": {
                "type": "string",
                "description": "The chat session ID for this proposal.",
            },
        },
        "required": ["file_path", "content", "description", "session_id"],
    },
)
async def propose_new_file(
    file_path: str,
    content: str,
    description: str,
    session_id: str,
):
    """Create a proposal to add a new file."""
    validated_session_id = _validate_or_generate_session_id(session_id)

    async with get_session() as db:
        service = ProposalService(db)

        try:
            # Create proposal
            proposal = await service.create_proposal(
                session_id=validated_session_id,
                description=description,
            )

            # Add file creation
            await service.add_file_change(
                proposal_id=str(proposal.id),
                file_path=file_path,
                operation="create",
                new_content=content,
            )

            # Check YOLO mode
            settings = await get_or_create_settings(db)
            auto_applied = False

            if settings.yolo_mode:
                # Auto-apply for creates (not deletes)
                await service.apply_proposal(str(proposal.id))
                auto_applied = True
                status = "applied"
            else:
                status = "pending"

            await db.commit()

            return {
                "proposal_id": str(proposal.id),
                "status": status,
                "auto_applied": auto_applied,
                "file_path": file_path,
                "content_length": len(content),
                "message": "File created automatically" if auto_applied else "Proposal created. User can review and approve.",
            }

        except ProposalError as e:
            logger.error(f"Proposal error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating proposal: {e}")
            return {"error": str(e)}


@tool(
    name="propose_delete_file",
    description="Propose deleting a file from the vault. This action always requires manual approval, even in YOLO mode.",
    parameters={
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Vault-relative path to the file to delete.",
            },
            "description": {
                "type": "string",
                "description": "Human-readable explanation of why this file should be deleted.",
            },
            "session_id": {
                "type": "string",
                "description": "The chat session ID for this proposal.",
            },
        },
        "required": ["file_path", "description", "session_id"],
    },
)
async def propose_delete_file(
    file_path: str,
    description: str,
    session_id: str,
):
    """Create a proposal to delete a file. Always requires manual approval."""
    validated_session_id = _validate_or_generate_session_id(session_id)

    async with get_session() as db:
        service = ProposalService(db)

        try:
            # Create proposal
            proposal = await service.create_proposal(
                session_id=validated_session_id,
                description=description,
            )

            # Add file deletion
            await service.add_file_change(
                proposal_id=str(proposal.id),
                file_path=file_path,
                operation="delete",
                new_content=None,
            )

            await db.commit()

            # Deletes NEVER auto-apply, even in YOLO mode
            return {
                "proposal_id": str(proposal.id),
                "status": "pending",
                "requires_approval": True,
                "file_path": file_path,
                "message": "Delete proposals always require manual approval for safety.",
            }

        except ProposalError as e:
            logger.error(f"Proposal error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error creating proposal: {e}")
            return {"error": str(e)}


def register_proposal_tools():
    """Register all proposal tools. Called from register_all_tools()."""
    # Tools are registered via @tool decorator when module is imported
    logger.info("Proposal tools registered")
