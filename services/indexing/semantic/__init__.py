"""Semantic search with E5-multilingual embeddings."""

from .embeddings import EmbeddingModel
from .chunker import MarkdownChunker, Chunk
from .searcher import VaultSearcher

__all__ = ["EmbeddingModel", "MarkdownChunker", "Chunk", "VaultSearcher"]
