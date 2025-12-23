"""Vault Git API Endpoints

Provides HTTP endpoints for managing vault git operations.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.git_service import VaultGitService, GitStatus
from core.config import get_settings

router = APIRouter(prefix="/vault/git", tags=["vault-git"])


class SyncRequest(BaseModel):
    """Request model for sync operation"""
    commit_message: Optional[str] = None


@router.get("/status", response_model=GitStatus)
async def get_vault_git_status():
    """Get current git status of vault"""
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    return await git_service.get_status()


@router.post("/sync")
async def sync_vault_git(request: SyncRequest = None):
    """Pull, commit all changes, push
    
    This performs a full sync cycle:
    1. Pull latest changes from remote
    2. Commit any uncommitted changes
    3. Push to remote
    """
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    
    if not git_service.is_git_repo:
        raise HTTPException(
            status_code=400,
            detail="Vault is not a git repository"
        )
    
    result = await git_service.sync()
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Sync failed")
        )
    
    return result


@router.get("/diff")
async def get_vault_diff(file_path: Optional[str] = None):
    """Get diff for file or entire vault
    
    Args:
        file_path: Optional path to specific file. If not provided, shows diff for all changes.
    """
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    
    if not git_service.is_git_repo:
        raise HTTPException(
            status_code=400,
            detail="Vault is not a git repository"
        )
    
    diff = await git_service.get_diff(file_path)
    return {"diff": diff, "file_path": file_path}


@router.post("/commit")
async def commit_vault_changes(
    message: str,
    files: Optional[list[str]] = None
):
    """Commit specific files or all changes
    
    Args:
        message: Commit message
        files: Optional list of file paths to commit. If not provided, commits all changes.
    """
    settings = get_settings()
    git_service = VaultGitService(settings.obsidian_vault_path)
    
    if not git_service.is_git_repo:
        raise HTTPException(
            status_code=400,
            detail="Vault is not a git repository"
        )
    
    result = await git_service.commit_changes(message, files)
    
    if not result["success"]:
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Commit failed")
        )
    
    return result
