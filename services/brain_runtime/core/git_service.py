"""Vault Git Management Service

Provides git operations for Obsidian vault with auto-commit support.
"""

import logging
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

try:
    import git
except ImportError:
    git = None

logger = logging.getLogger(__name__)


class GitStatus(BaseModel):
    """Git status for vault"""
    is_git_repo: bool
    last_commit: Optional[dict] = None
    uncommitted_files: list[str] = []
    is_dirty: bool = False
    remote_ahead: int = 0
    remote_behind: int = 0


class VaultGitService:
    """Service for managing vault git operations"""
    
    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.repo: Optional[git.Repo] = None
        self.is_git_repo = False
        
        if git is None:
            logger.warning("GitPython not installed. Git features disabled.")
            return
            
        try:
            self.repo = git.Repo(vault_path)
            self.is_git_repo = True
            logger.info(f"Git repository found at {vault_path}")
        except git.InvalidGitRepositoryError:
            logger.info(f"No git repository at {vault_path}")
            self.is_git_repo = False
        except Exception as e:
            logger.error(f"Error initializing git repo: {e}")
            self.is_git_repo = False

    async def get_status(self) -> GitStatus:
        """Get current git status"""
        if not self.is_git_repo or not self.repo:
            return GitStatus(is_git_repo=False)

        try:
            # Get last commit
            last_commit = None
            if self.repo.head.is_valid():
                commit = self.repo.head.commit
                last_commit = {
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                    "sha": commit.hexsha[:7]
                }

            # Get uncommitted files
            uncommitted = [
                item.a_path for item in self.repo.index.diff(None)
            ] + self.repo.untracked_files

            # Check remote status
            remote_ahead = 0
            remote_behind = 0
            try:
                # Try to get remote tracking branch
                tracking_branch = self.repo.active_branch.tracking_branch()
                if tracking_branch:
                    remote_ahead = len(list(self.repo.iter_commits(f'{tracking_branch}..HEAD')))
                    remote_behind = len(list(self.repo.iter_commits(f'HEAD..{tracking_branch}')))
            except Exception as e:
                logger.debug(f"Could not get remote status: {e}")
                # No remote or not fetched

            return GitStatus(
                last_commit=last_commit,
                uncommitted_files=uncommitted,
                is_dirty=self.repo.is_dirty(untracked_files=True),
                remote_ahead=remote_ahead,
                remote_behind=remote_behind,
                is_git_repo=True
            )
        except Exception as e:
            logger.error(f"Error getting git status: {e}")
            return GitStatus(is_git_repo=False)

    async def commit_changes(
        self,
        message: str,
        files: Optional[list[str]] = None
    ) -> dict:
        """Commit specific files or all changes"""
        if not self.is_git_repo or not self.repo:
            return {"success": False, "error": "Not a git repository"}

        try:
            if files:
                # Add specific files
                self.repo.index.add(files)
            else:
                # Add all changes
                self.repo.git.add(A=True)

            # Commit
            self.repo.index.commit(message)
            logger.info(f"Committed changes: {message}")
            
            return {"success": True, "message": "Changes committed"}
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return {"success": False, "error": str(e)}

    async def sync(self) -> dict:
        """Pull, commit, push workflow"""
        if not self.is_git_repo or not self.repo:
            return {"success": False, "error": "Not a git repository"}

        try:
            # Pull first
            try:
                self.repo.git.pull()
                logger.info("Pulled latest changes")
            except git.GitCommandError as e:
                logger.warning(f"Pull failed (may be expected): {e}")

            # Commit if dirty
            if self.repo.is_dirty(untracked_files=True):
                result = await self.commit_changes("Auto-sync from Second Brain")
                if not result["success"]:
                    return result

            # Push
            try:
                self.repo.git.push()
                logger.info("Pushed changes to remote")
            except git.GitCommandError as e:
                logger.warning(f"Push failed: {e}")
                return {"success": False, "error": f"Push failed: {str(e)}"}

            return {"success": True, "message": "Synced successfully"}
        except Exception as e:
            logger.error(f"Error syncing: {e}")
            return {"success": False, "error": str(e)}

    async def get_diff(self, file_path: Optional[str] = None) -> str:
        """Get diff for file or all changes"""
        if not self.is_git_repo or not self.repo:
            return ""

        try:
            if file_path:
                return self.repo.git.diff(file_path)
            else:
                return self.repo.git.diff()
        except Exception as e:
            logger.error(f"Error getting diff: {e}")
            return ""
