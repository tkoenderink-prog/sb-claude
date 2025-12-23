"""
Markdown chunking module.

Implements hybrid heading-aware + token-based chunking for markdown documents.
"""

import re
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""
    chunk_id: str
    text: str
    title: str
    file_path: str
    heading_path: str
    para_category: str
    tags: List[str]
    links: List[str]
    start_line: int
    end_line: int
    token_count: int


class MarkdownChunker:
    """
    Chunks markdown documents using heading-aware + token-based hybrid strategy.

    Strategy:
    1. Split by headings (H1, H2, H3) to preserve semantic structure
    2. If a section exceeds max_tokens, split further by tokens
    3. Maintain overlap between chunks for context continuity
    """

    def __init__(
        self,
        max_tokens: int = 800,
        overlap_tokens: int = 120,
        min_chunk_size: int = 50,
        vault_root: Optional[Path] = None,
        vault_name: str = "Obsidian-Private"
    ):
        """Initialize chunker with configuration."""
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_chunk_size = min_chunk_size
        self.vault_root = vault_root
        self.vault_name = vault_name

        # Use tiktoken for accurate token counting
        import tiktoken
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        self.logger = logging.getLogger(__name__)

    def chunk_file(self, file_path: Path) -> List[Chunk]:
        """
        Chunk a markdown file into semantic chunks.

        Args:
            file_path: Path to markdown file

        Returns:
            List of Chunk objects
        """
        # Read file content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            self.logger.warning(f"UTF-8 decode error in {file_path.name}")

        # Parse frontmatter
        content, metadata = self._parse_frontmatter(content)

        # Extract metadata
        title = file_path.stem
        relative_path = str(file_path.relative_to(self.vault_root)) if self.vault_root else str(file_path)
        para_category = self._detect_para_category(relative_path)
        tags = self._extract_tags(metadata, content)

        # Split by headings first
        sections = self._split_by_headings(content)

        # Generate chunks
        chunks = []
        for heading_path, section_text, start_line in sections:
            # Extract links from this section
            links = self._extract_links(section_text)

            # Count tokens
            token_count = self._count_tokens(section_text)

            if token_count <= self.max_tokens:
                # Section fits in one chunk
                if token_count >= self.min_chunk_size:
                    chunk_id = self._generate_chunk_id(relative_path, heading_path, start_line)
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        text=section_text.strip(),
                        title=title,
                        file_path=relative_path,
                        heading_path=heading_path,
                        para_category=para_category,
                        tags=tags,
                        links=links,
                        start_line=start_line,
                        end_line=start_line + section_text.count('\n'),
                        token_count=token_count
                    ))
            else:
                # Section too large, split by tokens
                sub_chunks = self._split_by_tokens(section_text, start_line)
                for i, (sub_chunk_text, sub_start_line) in enumerate(sub_chunks):
                    chunk_id = self._generate_chunk_id(relative_path, heading_path, sub_start_line)
                    chunks.append(Chunk(
                        chunk_id=chunk_id,
                        text=sub_chunk_text.strip(),
                        title=title,
                        file_path=relative_path,
                        heading_path=heading_path,
                        para_category=para_category,
                        tags=tags,
                        links=self._extract_links(sub_chunk_text),
                        start_line=sub_start_line,
                        end_line=sub_start_line + sub_chunk_text.count('\n'),
                        token_count=self._count_tokens(sub_chunk_text)
                    ))

        self.logger.debug(f"Chunked {file_path.name}: {len(chunks)} chunks")
        return chunks

    def _parse_frontmatter(self, content: str) -> Tuple[str, Dict]:
        """Parse YAML frontmatter from content."""
        metadata = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    metadata = yaml.safe_load(parts[1]) or {}
                    content = parts[2]
                except Exception:
                    pass
        return content, metadata

    def _split_by_headings(self, content: str) -> List[Tuple[str, str, int]]:
        """
        Split content by markdown headings.

        Returns:
            List of (heading_path, section_text, start_line) tuples
        """
        lines = content.splitlines()
        sections = []
        current_section = []
        heading_stack = []
        section_start_line = 0

        for i, line in enumerate(lines):
            # Check if line is a heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if heading_match:
                # Save previous section
                if current_section:
                    heading_path = " > ".join(heading_stack) if heading_stack else "ROOT"
                    section_text = "\n".join(current_section)
                    if section_text.strip():
                        sections.append((heading_path, section_text, section_start_line))

                # Update heading stack
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Trim stack to current level
                heading_stack = heading_stack[:level-1]
                heading_stack.append(heading_text)

                # Start new section
                current_section = []
                section_start_line = i + 1
            else:
                current_section.append(line)

        # Add final section
        if current_section:
            heading_path = " > ".join(heading_stack) if heading_stack else "ROOT"
            section_text = "\n".join(current_section)
            if section_text.strip():
                sections.append((heading_path, section_text, section_start_line))

        return sections

    def _split_by_tokens(self, text: str, start_line: int) -> List[Tuple[str, int]]:
        """
        Split text by tokens with overlap.

        Returns:
            List of (chunk_text, start_line) tuples
        """
        tokens = self.tokenizer.encode(text)
        chunks = []

        i = 0
        while i < len(tokens):
            # Take max_tokens
            chunk_tokens = tokens[i:i + self.max_tokens]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append((chunk_text, start_line + i // 10))  # Approximate line number

            # Move forward by (max_tokens - overlap_tokens)
            i += self.max_tokens - self.overlap_tokens

        return chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def _detect_para_category(self, path: str) -> str:
        """Detect PARA category from file path."""
        path_lower = path.lower()
        if '01-projects' in path_lower:
            return 'PROJECT'
        elif '02-areas' in path_lower:
            return 'AREA'
        elif '03-resources' in path_lower:
            return 'RESOURCE'
        elif '04-archive' in path_lower:
            return 'ARCHIVE'
        elif '00-inbox' in path_lower:
            return 'INBOX'
        else:
            return 'UNKNOWN'

    def _extract_tags(self, frontmatter: Dict, content: str) -> List[str]:
        """Extract tags from frontmatter and inline #tags."""
        tags = set()

        # From frontmatter
        if 'tags' in frontmatter:
            fm_tags = frontmatter['tags']
            if isinstance(fm_tags, str):
                tags.add(fm_tags if fm_tags.startswith('#') else f'#{fm_tags}')
            elif isinstance(fm_tags, list):
                for tag in fm_tags:
                    if tag:
                        tags.add(tag if str(tag).startswith('#') else f'#{tag}')

        # From inline #tags
        inline_tags = re.findall(r'#[\w\-]+', content)
        tags.update(inline_tags)

        return sorted(list(tags))

    def _extract_links(self, text: str) -> List[str]:
        """Extract [[wiki-style]] links from text."""
        links = re.findall(r'\[\[([^\]]+)\]\]', text)
        return list(set(links))  # Deduplicate

    def _generate_chunk_id(self, path: str, heading: str, start_line: int) -> str:
        """Generate stable chunk ID from path + heading + line."""
        key = f"{path}|{heading}|{start_line}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
