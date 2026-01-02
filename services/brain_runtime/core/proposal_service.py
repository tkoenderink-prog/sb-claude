"""Proposal service for managing file change proposals."""

import difflib
import shutil
import uuid
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import ProposalDB, ProposalFileDB, UserSettingsDB
from core.config import get_settings
from core.git_service import VaultGitService

logger = logging.getLogger(__name__)
settings = get_settings()


class ProposalError(Exception):
    """Base exception for proposal errors."""
    pass


class FileNotFoundError(ProposalError):
    """File does not exist in vault (for modify/delete)."""
    pass


class FileExistsError(ProposalError):
    """File already exists (for create)."""
    pass


class ApplyError(ProposalError):
    """Failed to apply changes (permissions, disk space, etc.)."""
    pass


class BackupError(ProposalError):
    """Failed to create backup."""
    pass


def get_vault_path() -> Path:
    """Get the vault root path."""
    vault_path = settings.get_vault_path()
    if not vault_path:
        raise ProposalError("Obsidian vault path not configured")
    return Path(vault_path)


def validate_vault_path(file_path: str) -> Path:
    """
    Validate that file_path is within the vault.
    Raises ProposalError if path escapes vault.
    """
    vault_path = get_vault_path()
    full_path = vault_path / file_path

    # Security: ensure path is within vault
    try:
        full_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise ProposalError(f"Path outside vault: {file_path}")

    return full_path


def get_backup_base_path() -> Path:
    """Get the backup directory base path."""
    return Path(__file__).parent.parent.parent / "data" / "backups"


class ProposalService:
    """Service for managing file change proposals."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_proposal(
        self,
        session_id: str,
        description: str,
    ) -> ProposalDB:
        """Create new proposal in pending state."""
        proposal = ProposalDB(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            status="pending",
            description=description,
        )
        self.db.add(proposal)
        await self.db.flush()
        return proposal

    async def add_file_change(
        self,
        proposal_id: str,
        file_path: str,
        operation: Literal["create", "modify", "delete"],
        new_content: Optional[str] = None,
    ) -> ProposalFileDB:
        """Add a file change to an existing proposal."""
        # Validate path is within vault
        full_path = validate_vault_path(file_path)

        original_content = None
        diff_hunks = None

        if operation == "create":
            if full_path.exists():
                raise FileExistsError(f"File already exists: {file_path}")
        elif operation == "modify":
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            original_content = full_path.read_text(encoding="utf-8")
            if new_content:
                diff_hunks = self.generate_diff(original_content, new_content)
        elif operation == "delete":
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            original_content = full_path.read_text(encoding="utf-8")

        proposal_file = ProposalFileDB(
            id=uuid.uuid4(),
            proposal_id=uuid.UUID(proposal_id),
            file_path=file_path,
            operation=operation,
            original_content=original_content,
            proposed_content=new_content,
            diff_hunks=diff_hunks,
        )
        self.db.add(proposal_file)
        await self.db.flush()
        return proposal_file

    def generate_diff(self, original: str, proposed: str) -> List[dict]:
        """Generate unified diff hunks using difflib."""
        original_lines = original.splitlines(keepends=True)
        proposed_lines = proposed.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            original_lines,
            proposed_lines,
            fromfile="original",
            tofile="proposed",
            lineterm="",
        ))

        # Parse diff into hunks
        hunks = []
        current_hunk = []
        for line in diff:
            if line.startswith("@@"):
                if current_hunk:
                    hunks.append({"lines": current_hunk})
                current_hunk = [line]
            elif current_hunk:
                current_hunk.append(line)

        if current_hunk:
            hunks.append({"lines": current_hunk})

        return hunks

    async def get_proposal(self, proposal_id: str) -> Optional[ProposalDB]:
        """Get a proposal by ID."""
        result = await self.db.execute(
            select(ProposalDB).where(ProposalDB.id == uuid.UUID(proposal_id))
        )
        return result.scalar_one_or_none()

    async def get_proposal_files(self, proposal_id: str) -> List[ProposalFileDB]:
        """Get all files for a proposal."""
        result = await self.db.execute(
            select(ProposalFileDB).where(
                ProposalFileDB.proposal_id == uuid.UUID(proposal_id)
            )
        )
        return list(result.scalars().all())

    async def approve_proposal(self, proposal_id: str) -> ProposalDB:
        """Mark proposal as approved (does not apply yet)."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ProposalError(f"Proposal not found: {proposal_id}")

        proposal.status = "approved"
        await self.db.flush()
        return proposal

    async def apply_proposal(self, proposal_id: str) -> ProposalDB:
        """Apply approved proposal changes with backup."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ProposalError(f"Proposal not found: {proposal_id}")

        files = await self.get_proposal_files(proposal_id)
        if not files:
            raise ProposalError(f"No files in proposal: {proposal_id}")

        # Create backup of original files
        file_paths = [f.file_path for f in files if f.operation in ("modify", "delete")]
        if file_paths:
            backup_path = await self.create_backup(file_paths)
            proposal.backup_path = backup_path

        # Apply changes
        try:
            for file in files:
                full_path = validate_vault_path(file.file_path)

                if file.operation == "create":
                    # Ensure parent directory exists
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_text(file.proposed_content or "", encoding="utf-8")
                    logger.info(f"Created file: {file.file_path}")

                elif file.operation == "modify":
                    full_path.write_text(file.proposed_content or "", encoding="utf-8")
                    logger.info(f"Modified file: {file.file_path}")

                elif file.operation == "delete":
                    full_path.unlink()
                    logger.info(f"Deleted file: {file.file_path}")

            proposal.status = "applied"
            proposal.applied_at = datetime.now(timezone.utc)
            await self.db.flush()

        except Exception as e:
            logger.error(f"Failed to apply proposal {proposal_id}: {e}")
            raise ApplyError(f"Failed to apply changes: {e}")

        return proposal

    async def apply_proposal_with_git(
        self,
        proposal_id: str,
        user_settings: Optional[dict] = None
    ) -> ProposalDB:
        """
        Apply proposal with git commits before and after.

        This is the recommended way to apply proposals as it creates safety checkpoints.
        """
        # Get user settings for git configuration
        if user_settings is None:
            stmt = select(UserSettingsDB).limit(1)
            result = await self.db.execute(stmt)
            settings_db = result.scalar_one_or_none()
            user_settings = settings_db.git_settings if settings_db and settings_db.git_settings else {}

        git_settings = user_settings if isinstance(user_settings, dict) else {}

        # Check if auto-commit is enabled
        auto_commit = git_settings.get('auto_commit_on_edit', True)
        auto_push = git_settings.get('auto_push', False)

        if not auto_commit:
            # If auto-commit disabled, just apply normally
            return await self.apply_proposal(proposal_id)

        # Initialize git service
        vault_path = str(get_vault_path())
        git_service = VaultGitService(vault_path)

        if not git_service.is_git_repo:
            logger.info("Vault is not a git repository, applying without git commits")
            return await self.apply_proposal(proposal_id)

        # Get proposal for commit message
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ProposalError(f"Proposal not found: {proposal_id}")

        # Get affected files for targeted commits
        files = await self.get_proposal_files(proposal_id)
        affected_files = [f.file_path for f in files]

        # Pre-edit commit: only commit files that already exist
        vault_path = Path(vault_path)
        existing_files = [
            f for f in affected_files
            if (vault_path / f).exists()
        ]

        try:
            # Pre-edit commit (safety checkpoint) - only for existing files
            if existing_files:
                pre_commit_msg = f"Pre-edit: {proposal.description}"
                pre_commit_result = await git_service.commit_changes(
                    message=pre_commit_msg,
                    files=existing_files
                )
                if not pre_commit_result.get('success'):
                    logger.warning(f"Pre-edit commit failed: {pre_commit_result.get('error')}")
                    # Continue anyway - pre-edit is optional safety feature
                else:
                    logger.info(f"Pre-edit commit: {pre_commit_msg}")

            # Apply the proposal
            result = await self.apply_proposal(proposal_id)

            # Post-edit commit - commit all affected files (now they all exist)
            template = git_settings.get('commit_message_template', '[Second Brain] {action}')
            post_commit_msg = template.replace('{action}', f"Applied: {proposal.description}")
            post_commit_result = await git_service.commit_changes(
                message=post_commit_msg,
                files=affected_files if affected_files else None
            )

            if not post_commit_result.get('success'):
                logger.error(f"Post-edit commit failed: {post_commit_result.get('error')}")
                # This is more serious - we've changed files but can't commit
                # However, files are still safely modified, just not committed
            else:
                logger.info(f"Post-edit commit: {post_commit_msg}")

            # Auto-push if enabled (only if post-commit succeeded)
            if auto_push and post_commit_result.get('success'):
                sync_result = await git_service.sync()
                if sync_result.get('success'):
                    logger.info("Auto-pushed changes to remote")
                else:
                    logger.warning(f"Auto-push failed: {sync_result.get('error')}")

            return result

        except Exception as e:
            logger.error(f"Error in apply_proposal_with_git: {e}")
            raise ProposalError(f"Failed to apply proposal with git: {str(e)}")

    async def reject_proposal(self, proposal_id: str) -> ProposalDB:
        """Mark proposal as rejected."""
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ProposalError(f"Proposal not found: {proposal_id}")

        proposal.status = "rejected"
        await self.db.flush()
        return proposal

    async def create_backup(self, file_paths: List[str]) -> str:
        """Copy originals to data/backups/{timestamp}/, return backup path."""
        # Clean up old backups first
        await self.cleanup_old_backups()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = get_backup_base_path() / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        vault_path = get_vault_path()

        try:
            for file_path in file_paths:
                full_path = vault_path / file_path
                if full_path.exists():
                    backup_file_path = backup_dir / file_path
                    backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_path, backup_file_path)
                    logger.info(f"Backed up: {file_path}")
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise BackupError(f"Failed to create backup: {e}")

        return str(backup_dir)

    async def cleanup_old_backups(self, max_age_days: int = 30) -> int:
        """Remove backups older than max_age_days, return count deleted."""
        backup_base = get_backup_base_path()
        if not backup_base.exists():
            return 0

        cutoff = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0

        for backup_dir in backup_base.iterdir():
            if not backup_dir.is_dir():
                continue

            try:
                # Parse timestamp from directory name (YYYYMMDD_HHMMSS)
                dir_name = backup_dir.name
                backup_time = datetime.strptime(dir_name, "%Y%m%d_%H%M%S")

                if backup_time < cutoff:
                    shutil.rmtree(backup_dir)
                    deleted_count += 1
                    logger.info(f"Cleaned up old backup: {dir_name}")
            except (ValueError, OSError) as e:
                logger.warning(f"Could not process backup dir {backup_dir}: {e}")

        return deleted_count


async def get_or_create_settings(db: AsyncSession) -> UserSettingsDB:
    """Get or create the singleton settings row."""
    result = await db.execute(select(UserSettingsDB).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = UserSettingsDB()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings
