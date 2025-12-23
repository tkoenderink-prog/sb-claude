"""Vault access and search endpoints."""

import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import subprocess
import json

from core.config import get_settings

# Add services to path
services_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(services_path))

router = APIRouter(prefix="/vault", tags=["vault"])

settings = get_settings()
app_root = Path(__file__).parent.parent.parent.parent


class SearchResult(BaseModel):
    """A single search result."""

    chunk_id: Optional[str] = None
    score: Optional[float] = None
    text: str
    title: str
    file_path: str
    heading_path: Optional[str] = None
    para_category: Optional[str] = None
    tags: list[str] = []
    links: list[str] = []
    obsidian_uri: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    token_count: Optional[int] = None
    search_type: str = "semantic"


class SearchResponse(BaseModel):
    """Search results response."""

    query: str
    results: list[SearchResult]
    count: int
    search_type: str


class SearchStatsResponse(BaseModel):
    """Search index statistics."""

    semantic: dict
    text_search_available: bool


@router.get("/search/status", response_model=SearchStatsResponse)
async def get_search_status():
    """Get status of search indexes."""
    # Check semantic index
    persist_dir = app_root / "data" / "chroma"

    semantic_stats = {"status": "not_indexed", "chunk_count": 0}

    if persist_dir.exists():
        try:
            from indexing.semantic.searcher import VaultSearcher

            searcher = VaultSearcher(
                persist_directory=persist_dir,
                collection_name="vault_chunks",
                vault_name="Obsidian-Private",
            )
            semantic_stats = searcher.get_stats()
        except Exception as e:
            semantic_stats = {"status": "error", "error": str(e)}

    # Check if ripgrep is available
    try:
        subprocess.run(["rg", "--version"], capture_output=True, check=True)
        text_search = True
    except Exception:
        text_search = False

    return SearchStatsResponse(
        semantic=semantic_stats, text_search_available=text_search
    )


async def search_vault(
    query: str,
    search_type: str = "semantic",
    top_k: int = 8,
    min_score: float = 0.0,
    para_category: Optional[str] = None,
    tags: Optional[str] = None,
    path_contains: Optional[str] = None,
) -> SearchResponse:
    """
    Search vault content (internal function).

    This function can be called directly from tools or via the HTTP endpoint.

    - semantic: Uses E5-multilingual embeddings for meaning-based search
    - text: Uses ripgrep for exact text matching
    - hybrid: Combines both (semantic first, text as fallback)
    """
    tag_list = tags.split(",") if tags else None

    if search_type in ("semantic", "hybrid"):
        results = await _semantic_search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            para_category=para_category,
            tags=tag_list,
            path_contains=path_contains,
        )

        if results or search_type == "semantic":
            return SearchResponse(
                query=query, results=results, count=len(results), search_type="semantic"
            )

    if search_type in ("text", "hybrid"):
        results = await _text_search(
            query=query, top_k=top_k, path_contains=path_contains
        )

        return SearchResponse(
            query=query, results=results, count=len(results), search_type="text"
        )

    raise HTTPException(status_code=400, detail=f"Invalid search_type: {search_type}")


@router.post("/search", response_model=SearchResponse)
async def search_vault_endpoint(
    query: str,
    search_type: str = Query(
        "semantic", description="Search type: semantic, text, or hybrid"
    ),
    top_k: int = Query(8, ge=1, le=50, description="Number of results"),
    min_score: float = Query(
        0.0, ge=0.0, le=1.0, description="Minimum similarity score"
    ),
    para_category: Optional[str] = Query(None, description="Filter by PARA category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    path_contains: Optional[str] = Query(None, description="Filter by path substring"),
):
    """HTTP endpoint for vault search."""
    return await search_vault(
        query=query,
        search_type=search_type,
        top_k=top_k,
        min_score=min_score,
        para_category=para_category,
        tags=tags,
        path_contains=path_contains,
    )


async def _semantic_search(
    query: str,
    top_k: int,
    min_score: float,
    para_category: Optional[str],
    tags: Optional[list[str]],
    path_contains: Optional[str],
) -> list[SearchResult]:
    """Perform semantic search using ChromaDB."""
    persist_dir = app_root / "data" / "chroma"

    if not persist_dir.exists():
        return []

    try:
        from indexing.semantic.searcher import VaultSearcher

        searcher = VaultSearcher(
            persist_directory=persist_dir,
            collection_name="vault_chunks",
            vault_name="Obsidian-Private",
        )

        results = searcher.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            para_category=para_category,
            tags=tags,
            path_contains=path_contains,
        )

        return [
            SearchResult(
                chunk_id=r.get("chunk_id"),
                score=r.get("score"),
                text=r.get("text", ""),
                title=r.get("title", ""),
                file_path=r.get("file_path", ""),
                heading_path=r.get("heading_path"),
                para_category=r.get("para_category"),
                tags=r.get("tags", []),
                links=r.get("links", []),
                obsidian_uri=r.get("obsidian_uri", ""),
                start_line=r.get("start_line"),
                end_line=r.get("end_line"),
                token_count=r.get("token_count"),
                search_type="semantic",
            )
            for r in results
        ]
    except Exception as e:
        # Log error and return empty
        import logging

        logging.error(f"Semantic search failed: {e}")
        return []


async def _text_search(
    query: str, top_k: int, path_contains: Optional[str]
) -> list[SearchResult]:
    """Perform text search using ripgrep."""
    vault_path = Path(settings.obsidian_location) / "Obsidian-Private"

    if not vault_path.exists():
        return []

    try:
        # Build ripgrep command
        cmd = [
            "rg",
            "--json",
            "--max-count",
            str(top_k * 2),  # Get more results to filter
            "--type",
            "md",
            "--ignore-case",
            query,
            str(vault_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode not in (0, 1):  # 0 = matches, 1 = no matches
            return []

        results = []
        seen_files = set()

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            try:
                data = json.loads(line)
                if data.get("type") != "match":
                    continue

                match_data = data.get("data", {})
                file_path = match_data.get("path", {}).get("text", "")

                # Apply path filter
                if path_contains and path_contains.lower() not in file_path.lower():
                    continue

                # Skip duplicates
                if file_path in seen_files:
                    continue
                seen_files.add(file_path)

                # Get relative path
                try:
                    rel_path = str(Path(file_path).relative_to(vault_path))
                except ValueError:
                    rel_path = file_path

                line_number = match_data.get("line_number", 1)
                lines = match_data.get("lines", {})
                text = lines.get("text", "").strip() if isinstance(lines, dict) else ""

                # Build Obsidian URI
                from urllib.parse import quote

                obsidian_uri = (
                    f"obsidian://open?vault=Obsidian-Private&file={quote(rel_path)}"
                )

                results.append(
                    SearchResult(
                        text=text,
                        title=Path(file_path).stem,
                        file_path=rel_path,
                        obsidian_uri=obsidian_uri,
                        start_line=line_number,
                        search_type="text",
                    )
                )

                if len(results) >= top_k:
                    break

            except json.JSONDecodeError:
                continue

        return results

    except subprocess.TimeoutExpired:
        return []
    except Exception as e:
        import logging

        logging.error(f"Text search failed: {e}")
        return []


async def read_file(path: str):
    """
    Read a file from the vault (internal function).

    Can be called directly from tools or via the HTTP endpoint.
    """
    vault_path = Path(settings.obsidian_location) / "Obsidian-Private"
    file_path = vault_path / path

    # Security: ensure path is within vault
    try:
        file_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path outside vault")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="Path is not a file")

    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        content = file_path.read_text(encoding="utf-8", errors="replace")

    return {"path": path, "content": content, "size": file_path.stat().st_size}


@router.get("/read")
async def read_file_endpoint(
    path: str = Query(..., description="Vault-relative path to file"),
):
    """HTTP endpoint to read a file from the vault."""
    return await read_file(path=path)


async def list_directory(path: str = ""):
    """
    List files and directories in the vault (internal function).

    Can be called directly from tools or via the HTTP endpoint.
    """
    vault_path = Path(settings.obsidian_location) / "Obsidian-Private"
    dir_path = vault_path / path if path else vault_path

    # Security: ensure path is within vault
    try:
        dir_path.resolve().relative_to(vault_path.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Path outside vault")

    if not dir_path.exists():
        raise HTTPException(status_code=404, detail="Directory not found")

    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    items = []
    for item in sorted(dir_path.iterdir()):
        # Skip hidden files
        if item.name.startswith("."):
            continue

        rel_path = str(item.relative_to(vault_path))
        items.append(
            {
                "name": item.name,
                "path": rel_path,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            }
        )

    return {"path": path, "items": items, "count": len(items)}


@router.get("/list")
async def list_directory_endpoint(
    path: str = Query("", description="Vault-relative path to directory"),
):
    """HTTP endpoint to list files and directories in the vault."""
    return await list_directory(path=path)
