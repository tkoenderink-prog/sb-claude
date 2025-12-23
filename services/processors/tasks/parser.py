"""Task parser for extracting metadata from markdown task lines.

Parses Obsidian Tasks plugin syntax with custom time tracking extensions.
"""

import re
from pathlib import Path
from datetime import date
from typing import Optional
import urllib.parse
import logging

from .models import TaskItemV1


class TaskParser:
    """
    Parses markdown files for task checkboxes and metadata.

    Supports Obsidian Tasks plugin syntax with emoji-based metadata.
    """

    # Regex patterns (compiled for performance)
    TASK_LINE_PATTERN = re.compile(r'^[\s]*[-*] \[([ xX\/\-])\] (.+)$')
    DATE_PATTERN = re.compile(r'(\d{4}-\d{2}-\d{2})')
    TAG_PATTERN = re.compile(r'#[\w\-\/]+')
    CONTEXT_PATTERN = re.compile(r'@[\w\-]+')

    # Emoji-based metadata patterns
    DUE_PATTERN = re.compile(r'📅\s*(\d{4}-\d{2}-\d{2})')
    START_PATTERN = re.compile(r'🛫\s*(\d{4}-\d{2}-\d{2})')
    SCHEDULED_PATTERN = re.compile(r'🛬\s*(\d{4}-\d{2}-\d{2})')
    CREATED_PATTERN = re.compile(r'➕\s*(\d{4}-\d{2}-\d{2})')
    COMPLETED_PATTERN = re.compile(r'✅\s*(\d{4}-\d{2}-\d{2})')

    ESTIMATE_PATTERN = re.compile(r'⏱\s*(?:(\d+)h)?\s*(?:(\d+)m)?')
    ACTUAL_PATTERN = re.compile(r'🛎️\s*(?:(\d+)h)?\s*(?:(\d+)m)?')

    RECURRENCE_PATTERN = re.compile(r'🔁\s*([^📅🛫🛬➕✅⏱🛎️⏫🔼🔽#@\n]+)')

    # Priority emojis
    PRIORITY_HIGHEST = '⏫'
    PRIORITY_HIGH = '🔼'
    PRIORITY_LOW = '🔽'

    # Status mapping
    STATUS_MAP = {
        ' ': ('todo', False),
        'x': ('done', True),
        'X': ('done', True),
        '/': ('in_progress', False),
        '-': ('cancelled', False),
    }

    def __init__(self, vault_root: Path, vault_name: str):
        """
        Initialize task parser.

        Args:
            vault_root: Absolute path to vault root
            vault_name: Name of Obsidian vault (for URIs)
        """
        self.vault_root = vault_root
        self.vault_name = vault_name
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: Path) -> list[TaskItemV1]:
        """
        Parse a single markdown file for tasks.

        Args:
            file_path: Path to markdown file

        Returns:
            List of TaskItemV1 objects found in file
        """
        tasks: list[TaskItemV1] = []

        try:
            # Try UTF-8 first
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # Fallback to latin-1
                content = file_path.read_text(encoding='latin-1')
                self.logger.warning(f"Using latin-1 encoding for {file_path}")
            except Exception:
                # Final fallback: UTF-8 with errors ignored
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                self.logger.warning(f"Ignoring encoding errors for {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return tasks

        # Parse line by line
        lines = content.split('\n')
        in_code_block = False
        in_frontmatter = False

        for line_num, line in enumerate(lines, start=1):
            # Track code blocks
            if line.strip().startswith('```'):
                in_code_block = not in_code_block
                continue

            # Track frontmatter
            if line_num == 1 and line.strip() == '---':
                in_frontmatter = True
                continue
            if in_frontmatter and line.strip() == '---':
                in_frontmatter = False
                continue

            # Skip if in code block or frontmatter
            if in_code_block or in_frontmatter:
                continue

            # Try to parse as task
            task = self._parse_line(line, file_path, line_num)
            if task:
                tasks.append(task)

        return tasks

    def _parse_line(self, line: str, file_path: Path, line_num: int) -> Optional[TaskItemV1]:
        """
        Parse a single line as a task.

        Args:
            line: Line text
            file_path: Path to file containing this line
            line_num: Line number (1-based)

        Returns:
            TaskItemV1 object if line is a task, None otherwise
        """
        # Match task checkbox
        match = self.TASK_LINE_PATTERN.match(line)
        if not match:
            return None

        status_char = match.group(1)
        full_text = match.group(2)

        # Get status
        status, _ = self.STATUS_MAP.get(status_char, ('todo', False))

        # Get relative file path
        try:
            relative_path = file_path.relative_to(self.vault_root)
        except ValueError:
            relative_path = file_path

        relative_path_str = str(relative_path)

        # Generate task ID
        task_id = TaskItemV1.generate_task_id(relative_path_str, line_num)

        # Extract metadata
        due_date = self._extract_date(self.DUE_PATTERN, full_text)
        start_date = self._extract_date(self.START_PATTERN, full_text)
        scheduled_date = self._extract_date(self.SCHEDULED_PATTERN, full_text)
        created_date = self._extract_date(self.CREATED_PATTERN, full_text)
        completed_date = self._extract_date(self.COMPLETED_PATTERN, full_text)

        priority = self._extract_priority(full_text)
        recurrence = self._extract_recurrence(full_text)

        estimate_min = self._extract_time(self.ESTIMATE_PATTERN, full_text)
        actual_min = self._extract_time(self.ACTUAL_PATTERN, full_text)

        tags = self.TAG_PATTERN.findall(full_text)
        contexts = self.CONTEXT_PATTERN.findall(full_text)

        obsidian_uri = self._generate_uri(relative_path)

        return TaskItemV1(
            task_id=task_id,
            file_path=relative_path_str,
            line_number=line_num,
            text=full_text,
            text_clean=self._clean_text(full_text),
            status=status,
            due_date=due_date,
            scheduled_date=scheduled_date,
            start_date=start_date,
            created_date=created_date,
            completed_date=completed_date,
            priority=priority,
            tags=tags,
            contexts=contexts,
            estimate_min=estimate_min,
            actual_min=actual_min,
            recurrence=recurrence,
            obsidian_uri=obsidian_uri,
        )

    def _extract_date(self, pattern: re.Pattern, text: str) -> Optional[date]:
        """Extract date from text using pattern."""
        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            try:
                year, month, day = date_str.split('-')
                return date(int(year), int(month), int(day))
            except (ValueError, AttributeError):
                pass
        return None

    def _extract_priority(self, text: str) -> Optional[str]:
        """Extract priority from text."""
        if self.PRIORITY_HIGHEST in text:
            return "highest"
        elif self.PRIORITY_HIGH in text:
            return "high"
        elif self.PRIORITY_LOW in text:
            return "low"
        return None

    def _extract_recurrence(self, text: str) -> Optional[str]:
        """Extract recurrence pattern from text."""
        match = self.RECURRENCE_PATTERN.search(text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_time(self, pattern: re.Pattern, text: str) -> Optional[int]:
        """Extract time duration from text and convert to minutes."""
        match = pattern.search(text)
        if not match:
            return None

        hours_str = match.group(1)
        minutes_str = match.group(2)

        hours = int(hours_str) if hours_str else 0
        minutes = int(minutes_str) if minutes_str else 0

        total_minutes = (hours * 60) + minutes

        if total_minutes == 0:
            return None

        return total_minutes

    def _clean_text(self, text: str) -> str:
        """Clean task text by removing all metadata."""
        clean = text

        # Remove emoji-based metadata
        clean = re.sub(r'[📅🛫🛬➕✅]\s*\d{4}-\d{2}-\d{2}', '', clean)
        clean = re.sub(r'[⏱🛎️]\s*(?:\d+h)?\s*(?:\d+m)?', '', clean)
        clean = re.sub(r'🔁\s*[^📅🛫🛬➕✅⏱🛎️⏫🔼🔽#@\n]+', '', clean)
        clean = re.sub(r'[⏫🔼🔽]', '', clean)

        # Remove tags and contexts
        clean = re.sub(r'#[\w\-\/]+', '', clean)
        clean = re.sub(r'@[\w\-]+', '', clean)

        # Clean up extra whitespace
        clean = ' '.join(clean.split())

        return clean.strip()

    def _generate_uri(self, relative_path: Path) -> str:
        """Generate Obsidian URI for a file."""
        path_str = str(relative_path).replace('\\', '/')
        encoded_path = urllib.parse.quote(path_str)
        return f"obsidian://open?vault={self.vault_name}&file={encoded_path}"
