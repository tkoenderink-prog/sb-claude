"""RAG indexing processor - indexes vault for semantic search."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json
import logging

from ..base import BaseProcessor, ProcessorResult

logger = logging.getLogger(__name__)


class RAGProcessor(BaseProcessor):
    """Indexes vault markdown files for semantic search."""

    # Folders to include in indexing
    INCLUDE_FOLDERS = [
        '01-PROJECTS',
        '02-AREAS',
        '03-RESOURCES',
        '04-ARCHIVE',
        '01-Private',
    ]

    # Folders to exclude
    EXCLUDE_FOLDERS = [
        '.obsidian',
        '.trash',
        'templates',
        'Templates',
        '_templates',
    ]

    def __init__(
        self,
        exports_path: Path,
        vault_path: Path,
        data_path: Path,
        vault_name: str = "Obsidian-Private",
        recreate: bool = False
    ):
        """
        Args:
            exports_path: Path to exports directory
            vault_path: Path to Obsidian vault
            data_path: Path to data directory (for ChromaDB)
            vault_name: Name of Obsidian vault
            recreate: Whether to recreate the index from scratch
        """
        super().__init__(exports_path, "rag")
        self.vault_path = vault_path
        self.data_path = data_path
        self.vault_name = vault_name
        self.recreate = recreate

    async def run(self) -> ProcessorResult:
        """Index vault for semantic search."""
        started_at = datetime.now(timezone.utc)

        try:
            # Import indexing components
            import sys
            services_path = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(services_path))

            from indexing.semantic.chunker import MarkdownChunker
            from indexing.semantic.searcher import VaultSearcher

            logger.info(f"Starting RAG indexing for vault: {self.vault_path}")

            # Initialize chunker
            chunker = MarkdownChunker(
                max_tokens=800,
                overlap_tokens=120,
                min_chunk_size=50,
                vault_root=self.vault_path,
                vault_name=self.vault_name
            )

            # Initialize searcher (which handles the vector store)
            persist_dir = self.data_path / "chroma"
            searcher = VaultSearcher(
                persist_directory=persist_dir,
                collection_name="vault_chunks",
                vault_name=self.vault_name
            )

            # Clear if recreate requested
            if self.recreate:
                logger.info("Recreating index from scratch")
                searcher.clear()

            # Find all markdown files
            md_files = self._scan_vault()
            logger.info(f"Found {len(md_files)} markdown files to index")

            # Chunk all files
            all_chunks = []
            files_chunked = 0
            chunk_errors = 0

            for file_path in md_files:
                try:
                    chunks = chunker.chunk_file(file_path)
                    if chunks:
                        all_chunks.extend(chunks)
                        files_chunked += 1
                except Exception as e:
                    logger.error(f"Failed to chunk {file_path}: {e}")
                    chunk_errors += 1

            logger.info(f"Generated {len(all_chunks)} chunks from {files_chunked} files")

            # Index chunks
            indexed_count = searcher.index_chunks(all_chunks, batch_size=100)

            # Get final stats
            stats = searcher.get_stats()

            # Write summary to exports
            output_path = self.get_output_path("rag_index_v1.json")
            summary = {
                "version": "1.0",
                "indexed_at": started_at.isoformat(),
                "vault_root": str(self.vault_path),
                "vault_name": self.vault_name,
                "files_scanned": len(md_files),
                "files_chunked": files_chunked,
                "total_chunks": len(all_chunks),
                "chunks_indexed": indexed_count,
                "chunk_errors": chunk_errors,
                "collection_stats": stats
            }
            output_path.write_text(json.dumps(summary, indent=2))

            return ProcessorResult(
                success=True,
                processor_name=self.name,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
                output_path=str(output_path),
                metrics={
                    "files_scanned": len(md_files),
                    "files_chunked": files_chunked,
                    "total_chunks": len(all_chunks),
                    "chunks_indexed": indexed_count,
                    "chunk_errors": chunk_errors,
                    "collection_stats": stats
                }
            )

        except Exception as e:
            logger.error(f"RAG indexer failed: {e}", exc_info=True)
            return ProcessorResult(
                success=False,
                processor_name=self.name,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
                error=str(e)
            )

    def _scan_vault(self) -> list[Path]:
        """Scan vault for markdown files."""
        md_files: list[Path] = []

        # Start from include folders or vault root
        search_roots = []
        for folder in self.INCLUDE_FOLDERS:
            folder_path = self.vault_path / folder
            if folder_path.exists():
                search_roots.append(folder_path)

        # If no include folders exist, scan from vault root
        if not search_roots:
            search_roots = [self.vault_path]

        for root in search_roots:
            for md_file in root.rglob("*.md"):
                # Check if in excluded folder
                if self._should_exclude(md_file):
                    continue
                # Skip hidden files
                if md_file.name.startswith('.'):
                    continue
                md_files.append(md_file)

        return md_files

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded."""
        path_parts = file_path.parts
        for excluded in self.EXCLUDE_FOLDERS:
            if excluded in path_parts:
                return True
        return False
