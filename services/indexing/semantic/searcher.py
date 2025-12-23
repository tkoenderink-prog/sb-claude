"""
Semantic search module using ChromaDB.

Provides search interface for indexed vault chunks.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote
import logging
import json


class VaultSearcher:
    """
    Semantic search interface for indexed vault.

    Supports:
    - Semantic search with E5 embeddings
    - Metadata filtering (PARA category, tags, path)
    - Text search fallback
    """

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str = "vault_chunks",
        vault_name: str = "Obsidian-Private"
    ):
        """
        Initialize searcher.

        Args:
            persist_directory: Path to ChromaDB persistence directory
            collection_name: Name of the collection
            vault_name: Obsidian vault name for URI generation
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.vault_name = vault_name
        self.logger = logging.getLogger(__name__)

        # Lazy initialization
        self._client = None
        self._collection = None
        self._embedding_model = None

    @property
    def client(self):
        """Lazy load ChromaDB client."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings

            self.persist_directory.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
        return self._client

    @property
    def collection(self):
        """Get or create collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    @property
    def embedding_model(self):
        """Lazy load embedding model."""
        if self._embedding_model is None:
            from .embeddings import EmbeddingModel
            self._embedding_model = EmbeddingModel()
        return self._embedding_model

    def search(
        self,
        query: str,
        top_k: int = 8,
        min_score: float = 0.0,
        para_category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        path_contains: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search with optional filters.

        Args:
            query: Natural language search query
            top_k: Number of results
            min_score: Minimum similarity score (0.0-1.0)
            para_category: Filter by PARA category
            tags: Filter by tags (match any)
            path_contains: Filter by path substring

        Returns:
            List of search results with metadata and scores
        """
        # Check if collection has data
        if self.collection.count() == 0:
            self.logger.warning("No chunks indexed yet. Run indexer first.")
            return []

        # Build where filter for metadata
        where_filter = None
        if para_category:
            where_filter = {"para_category": para_category}

        # Generate query embedding
        self.logger.debug(f"Generating embedding for query: {query}")
        query_embedding = self.embedding_model.embed_query(query)

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k * 2 if path_contains or tags else top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        formatted_results = []

        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                distance = results['distances'][0][i] if results['distances'] else 0
                # ChromaDB returns distance, convert to similarity (cosine)
                score = 1 - distance

                if score < min_score:
                    continue

                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                text = results['documents'][0][i] if results['documents'] else ""

                # Parse tags and links from metadata (stored as JSON strings)
                chunk_tags = json.loads(metadata.get('tags', '[]')) if isinstance(metadata.get('tags'), str) else metadata.get('tags', [])
                chunk_links = json.loads(metadata.get('links', '[]')) if isinstance(metadata.get('links'), str) else metadata.get('links', [])

                # Apply tag filter
                if tags:
                    if not any(tag in chunk_tags for tag in tags):
                        continue

                # Apply path filter
                file_path = metadata.get('file_path', '')
                if path_contains and path_contains.lower() not in file_path.lower():
                    continue

                # Build Obsidian URI
                obsidian_uri = self._build_obsidian_uri(file_path)

                formatted_results.append({
                    "chunk_id": chunk_id,
                    "score": round(score, 4),
                    "text": text,
                    "title": metadata.get('title', ''),
                    "file_path": file_path,
                    "heading_path": metadata.get('heading_path', ''),
                    "para_category": metadata.get('para_category', ''),
                    "tags": chunk_tags,
                    "links": chunk_links,
                    "obsidian_uri": obsidian_uri,
                    "start_line": metadata.get('start_line'),
                    "end_line": metadata.get('end_line'),
                    "token_count": metadata.get('token_count')
                })

                if len(formatted_results) >= top_k:
                    break

        self.logger.info(f"Found {len(formatted_results)} results for query: {query}")
        return formatted_results

    def _build_obsidian_uri(self, file_path: str) -> str:
        """Build obsidian:// URI for file."""
        encoded_path = quote(file_path)
        return f"obsidian://open?vault={self.vault_name}&file={encoded_path}"

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about indexed collection."""
        try:
            count = self.collection.count()
            return {
                "collection": self.collection_name,
                "chunk_count": count,
                "persist_directory": str(self.persist_directory),
                "status": "ready" if count > 0 else "empty"
            }
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {"error": str(e), "status": "error"}

    def index_chunks(self, chunks: List[Any], batch_size: int = 100) -> int:
        """
        Index chunks into the vector store.

        Args:
            chunks: List of Chunk objects to index
            batch_size: Number of chunks per batch

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0

        self.logger.info(f"Indexing {len(chunks)} chunks...")

        # Generate embeddings for all chunks
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_model.embed_passages(texts, batch_size=batch_size)

        # Prepare data for ChromaDB
        ids = []
        documents = []
        metadatas = []
        embedding_list = []

        for i, chunk in enumerate(chunks):
            ids.append(chunk.chunk_id)
            documents.append(chunk.text)
            metadatas.append({
                "title": chunk.title,
                "file_path": chunk.file_path,
                "heading_path": chunk.heading_path,
                "para_category": chunk.para_category,
                "tags": json.dumps(chunk.tags),  # Store as JSON string
                "links": json.dumps(chunk.links),
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "token_count": chunk.token_count
            })
            embedding_list.append(embeddings[i].tolist())

        # Upsert in batches
        total_indexed = 0
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_embeddings = embedding_list[i:i + batch_size]

            self.collection.upsert(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
                embeddings=batch_embeddings
            )
            total_indexed += len(batch_ids)
            self.logger.debug(f"Indexed batch: {total_indexed}/{len(ids)}")

        self.logger.info(f"Successfully indexed {total_indexed} chunks")
        return total_indexed

    def clear(self):
        """Clear all indexed data."""
        try:
            self.client.delete_collection(self.collection_name)
            self._collection = None
            self.logger.info(f"Cleared collection: {self.collection_name}")
        except Exception as e:
            self.logger.warning(f"Failed to clear collection: {e}")
