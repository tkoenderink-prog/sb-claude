"""Tasks processor - scans vault and extracts tasks."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..base import BaseProcessor, ProcessorResult
from .parser import TaskParser
from .models import TaskItemV1

logger = logging.getLogger(__name__)


class TaskProcessor(BaseProcessor):
    """Processes tasks from Obsidian vault markdown files."""

    # Folders to include in scan
    INCLUDE_FOLDERS = [
        '01-PROJECTS',
        '02-AREAS',
        '03-RESOURCES',
        '04-ARCHIVE',
        '01-Private',
    ]

    # Folders to exclude from scan
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
        vault_name: str = "Obsidian-Private",
        db_session: Optional[AsyncSession] = None
    ):
        """
        Args:
            exports_path: Path to exports directory
            vault_path: Path to Obsidian vault
            vault_name: Name of Obsidian vault (for URIs)
            db_session: Optional database session for persisting tasks
        """
        super().__init__(exports_path, "tasks")
        self.vault_path = vault_path
        self.vault_name = vault_name
        self.db_session = db_session
        self.parser = TaskParser(vault_root=vault_path, vault_name=vault_name)

    async def run(self) -> ProcessorResult:
        """Scan vault and process all tasks."""
        started_at = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting task processing for vault: {self.vault_path}")

            # Find all markdown files
            md_files = self._scan_vault()
            logger.info(f"Found {len(md_files)} markdown files to scan")

            # Parse tasks from each file
            all_tasks: list[TaskItemV1] = []
            files_with_tasks = 0
            parse_errors = 0

            for file_path in md_files:
                try:
                    tasks = self.parser.parse_file(file_path)
                    if tasks:
                        all_tasks.extend(tasks)
                        files_with_tasks += 1
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    parse_errors += 1

            logger.info(f"Parsed {len(all_tasks)} tasks from {files_with_tasks} files")

            # Calculate statistics
            stats = self._calculate_stats(all_tasks)

            # Write JSON output
            output_path = self.get_output_path("tasks_v1.json")
            data = {
                "version": "1.0",
                "generated_at": started_at.isoformat(),
                "vault_root": str(self.vault_path),
                "vault_name": self.vault_name,
                "stats": stats,
                "tasks": [task.model_dump(mode='json') for task in all_tasks]
            }
            output_path.write_text(json.dumps(data, indent=2, default=str))

            # Insert tasks into database if session is available
            db_insert_count = 0
            if self.db_session and all_tasks:
                db_insert_count = await self._insert_tasks_to_db(all_tasks)
                logger.info(f"Inserted/updated {db_insert_count} tasks in database")

            return ProcessorResult(
                success=True,
                processor_name=self.name,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
                output_path=str(output_path),
                metrics={
                    "files_scanned": len(md_files),
                    "files_with_tasks": files_with_tasks,
                    "task_count": len(all_tasks),
                    "db_insert_count": db_insert_count,
                    "parse_errors": parse_errors,
                    "stats": stats,
                }
            )

        except Exception as e:
            logger.error(f"Tasks processor failed: {e}", exc_info=True)
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

    def _calculate_stats(self, tasks: list[TaskItemV1]) -> dict:
        """Calculate task statistics."""
        stats = {
            "total_tasks": len(tasks),
            "by_status": {
                "todo": 0,
                "done": 0,
                "in_progress": 0,
                "cancelled": 0,
            },
            "by_priority": {
                "highest": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "none": 0,
            },
            "with_due_date": 0,
            "overdue": 0,
        }

        today = datetime.now().date()

        for task in tasks:
            # Count by status
            stats["by_status"][task.status] = stats["by_status"].get(task.status, 0) + 1

            # Count by priority
            priority = task.priority or "none"
            if priority in stats["by_priority"]:
                stats["by_priority"][priority] += 1

            # Count with due date
            if task.due_date:
                stats["with_due_date"] += 1
                # Count overdue (not done and past due)
                if task.status not in ('done', 'cancelled') and task.due_date < today:
                    stats["overdue"] += 1

        return stats

    async def _insert_tasks_to_db(self, tasks: list[TaskItemV1]) -> int:
        """Insert or update tasks in the database."""
        try:
            from models.db_models import TaskDB

            # Prepare data, deduplicate by task_id
            seen = set()
            values = []
            for task in tasks:
                if task.task_id in seen:
                    continue
                seen.add(task.task_id)
                values.append({
                    "task_id": task.task_id,
                    "file_path": task.file_path,
                    "line_number": task.line_number,
                    "text": task.text,
                    "text_clean": task.text_clean,
                    "status": task.status,
                    "due_date": task.due_date,
                    "scheduled_date": task.scheduled_date,
                    "priority": task.priority,
                    "tags": task.tags,
                    "estimate_min": task.estimate_min,
                    "actual_min": task.actual_min,
                    "obsidian_uri": task.obsidian_uri,
                })

            if not values:
                return 0

            logger.info(f"Inserting {len(values)} unique tasks (deduplicated from {len(tasks)})")

            # Batch inserts
            BATCH_SIZE = 2000
            total_inserted = 0

            for i in range(0, len(values), BATCH_SIZE):
                batch = values[i:i + BATCH_SIZE]

                stmt = insert(TaskDB).values(batch)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["task_id"],
                    set_={
                        "file_path": stmt.excluded.file_path,
                        "line_number": stmt.excluded.line_number,
                        "text": stmt.excluded.text,
                        "text_clean": stmt.excluded.text_clean,
                        "status": stmt.excluded.status,
                        "due_date": stmt.excluded.due_date,
                        "scheduled_date": stmt.excluded.scheduled_date,
                        "priority": stmt.excluded.priority,
                        "tags": stmt.excluded.tags,
                        "estimate_min": stmt.excluded.estimate_min,
                        "actual_min": stmt.excluded.actual_min,
                        "obsidian_uri": stmt.excluded.obsidian_uri,
                    }
                )

                await self.db_session.execute(stmt)
                total_inserted += len(batch)

            await self.db_session.commit()
            return total_inserted

        except Exception as e:
            logger.error(f"Failed to insert tasks to database: {e}", exc_info=True)
            await self.db_session.rollback()
            return 0
