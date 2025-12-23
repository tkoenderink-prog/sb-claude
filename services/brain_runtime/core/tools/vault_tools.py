"""Vault/RAG tools wrapping the /vault API."""

from typing import Optional
import logging

from .registry import tool

logger = logging.getLogger(__name__)


@tool(
    name="semantic_search",
    description="Search vault content using semantic/meaning-based search with E5-multilingual embeddings. Best for finding conceptually related notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural language search query"},
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10, max: 50)",
                "default": 10,
            },
            "min_score": {
                "type": "number",
                "description": "Minimum similarity score (0.0 to 1.0, default: 0.0)",
                "default": 0.0,
            },
            "para_category": {
                "type": "string",
                "enum": ["Projects", "Areas", "Resources", "Archive"],
                "description": "Filter by PARA category",
            },
            "tags": {
                "type": "string",
                "description": "Filter by tags (comma-separated, e.g., '#work,#important')",
            },
            "path_contains": {
                "type": "string",
                "description": "Filter by path substring (e.g., 'journal' or 'mental-models')",
            },
        },
        "required": ["query"],
    },
)
async def semantic_search(
    query: str,
    limit: int = 10,
    min_score: float = 0.0,
    para_category: Optional[str] = None,
    tags: Optional[str] = None,
    path_contains: Optional[str] = None,
):
    """Semantic search across vault content."""
    from api.vault import search_vault

    result = await search_vault(
        query=query,
        search_type="semantic",
        top_k=limit,
        min_score=min_score,
        para_category=para_category,
        tags=tags,
        path_contains=path_contains,
    )

    return {
        "query": result.query,
        "results": [r.model_dump() for r in result.results],
        "count": result.count,
        "search_type": result.search_type,
    }


@tool(
    name="text_search",
    description="Search vault content using exact text matching with ripgrep. Best for finding specific words or phrases.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Text to search for (case-insensitive)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10, max: 50)",
                "default": 10,
            },
            "path_contains": {
                "type": "string",
                "description": "Filter by path substring (e.g., 'journal' or 'mental-models')",
            },
        },
        "required": ["query"],
    },
)
async def text_search(query: str, limit: int = 10, path_contains: Optional[str] = None):
    """Text search across vault content."""
    from api.vault import search_vault

    result = await search_vault(
        query=query, search_type="text", top_k=limit, path_contains=path_contains
    )

    return {
        "query": result.query,
        "results": [r.model_dump() for r in result.results],
        "count": result.count,
        "search_type": result.search_type,
    }


@tool(
    name="hybrid_search",
    description="Search vault using both semantic and text search. Tries semantic first, falls back to text if no results.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10, max: 50)",
                "default": 10,
            },
            "min_score": {
                "type": "number",
                "description": "Minimum similarity score for semantic search (0.0 to 1.0, default: 0.0)",
                "default": 0.0,
            },
            "path_contains": {
                "type": "string",
                "description": "Filter by path substring",
            },
        },
        "required": ["query"],
    },
)
async def hybrid_search(
    query: str,
    limit: int = 10,
    min_score: float = 0.0,
    path_contains: Optional[str] = None,
):
    """Hybrid search across vault content."""
    from api.vault import search_vault

    result = await search_vault(
        query=query,
        search_type="hybrid",
        top_k=limit,
        min_score=min_score,
        path_contains=path_contains,
    )

    return {
        "query": result.query,
        "results": [r.model_dump() for r in result.results],
        "count": result.count,
        "search_type": result.search_type,
    }


@tool(
    name="read_vault_file",
    description="Read the full content of a file from the vault. Path must be vault-relative (e.g., 'Projects/project-name/note.md').",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Vault-relative path to the file (e.g., 'Projects/example/note.md')",
            }
        },
        "required": ["path"],
    },
)
async def read_vault_file(path: str):
    """Read a file from the vault."""
    from api.vault import read_file

    result = await read_file(path=path)
    return result


@tool(
    name="list_vault_directory",
    description="List files and directories in a vault folder. Returns names, paths, types, and sizes.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Vault-relative path to directory (empty string for root)",
                "default": "",
            }
        },
        "required": [],
    },
)
async def list_vault_directory(path: str = ""):
    """List contents of a vault directory."""
    from api.vault import list_directory

    result = await list_directory(path=path)
    return result


def register_vault_tools():
    """Register all vault tools (called by decorator)."""
    # Tools are auto-registered by the @tool decorator
    logger.info("Vault tools registered")
