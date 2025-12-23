"""Calendar processor - fetches and normalizes calendar data."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..base import BaseProcessor, ProcessorResult
from .downloader import ICSDownloader
from .parser import ICSParser
from .models import NormalizedEventV1

logger = logging.getLogger(__name__)


class CalendarProcessor(BaseProcessor):
    """Processes calendar data from ICS URLs."""

    def __init__(
        self,
        exports_path: Path,
        ics_urls: dict[str, str],
        cache_dir: Path,
        timezone: str = "Europe/Amsterdam",
        db_session: Optional[AsyncSession] = None
    ):
        """
        Args:
            exports_path: Path to exports directory
            ics_urls: Dict of calendar names to ICS URLs (e.g., {'work': 'https://...', 'private': 'https://...'})
            cache_dir: Path to cache directory for ICS files
            timezone: Target timezone for events (default: Europe/Amsterdam)
            db_session: Optional database session for persisting events
        """
        super().__init__(exports_path, "calendar")
        self.ics_urls = ics_urls
        self.cache_dir = cache_dir
        self.timezone = timezone
        self.db_session = db_session

        # Initialize downloader and parser
        self.downloader = ICSDownloader(cache_dir=cache_dir, ttl_seconds=3600)
        self.parser = ICSParser(timezone=timezone)

    async def run(self) -> ProcessorResult:
        """Fetch and process calendar data."""
        started_at = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting calendar processing for {len(self.ics_urls)} calendars")

            all_events: list[NormalizedEventV1] = []

            # Process each calendar
            for calendar_name, ics_url in self.ics_urls.items():
                try:
                    logger.info(f"Processing calendar: {calendar_name}")

                    # Determine provider from URL
                    provider = self._detect_provider(ics_url)

                    # Download ICS content
                    ics_content = await self.downloader.download(ics_url, calendar_name)

                    # Parse ICS to Event objects
                    events = await self.parser.parse(ics_content, calendar_name)

                    # Convert to NormalizedEventV1
                    for event in events:
                        normalized_event = NormalizedEventV1.from_event(event, provider)
                        all_events.append(normalized_event)

                    logger.info(f"Processed {len(events)} events from {calendar_name}")

                except Exception as e:
                    logger.error(f"Failed to process calendar {calendar_name}: {e}")
                    # Continue processing other calendars
                    continue

            # Write combined output
            output_path = self.get_output_path("calendar_combined_v1.json")

            data = {
                "version": "1.0",
                "generated_at": started_at.isoformat(),
                "timezone": self.timezone,
                "calendars": list(self.ics_urls.keys()),
                "event_count": len(all_events),
                "events": [event.model_dump(mode='json') for event in all_events]
            }

            output_path.write_text(json.dumps(data, indent=2))

            logger.info(f"Successfully processed {len(all_events)} total events")

            # Insert events into database if session is available
            db_insert_count = 0
            if self.db_session and all_events:
                db_insert_count = await self._insert_events_to_db(all_events)
                logger.info(f"Inserted/updated {db_insert_count} events in database")

            return ProcessorResult(
                success=True,
                processor_name=self.name,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
                output_path=str(output_path),
                metrics={
                    "calendar_count": len(self.ics_urls),
                    "event_count": len(all_events),
                    "db_insert_count": db_insert_count,
                    "calendars_processed": list(self.ics_urls.keys())
                }
            )

        except Exception as e:
            logger.error(f"Calendar processor failed: {e}", exc_info=True)
            return ProcessorResult(
                success=False,
                processor_name=self.name,
                started_at=started_at,
                ended_at=datetime.now(timezone.utc),
                error=str(e)
            )

    async def _insert_events_to_db(self, events: list[NormalizedEventV1]) -> int:
        """
        Insert or update calendar events in the database.

        Uses PostgreSQL UPSERT (INSERT ... ON CONFLICT DO UPDATE) for efficiency.

        Args:
            events: List of NormalizedEventV1 events to insert

        Returns:
            Number of events inserted/updated
        """
        try:
            # Import here to avoid circular imports
            # When running via uvicorn from brain_runtime, models is directly accessible
            from models.db_models import CalendarEventDB

            # Prepare data for bulk upsert, deduplicate by (provider, event_id)
            seen = set()
            values = []
            for event in events:
                key = (event.provider, event.event_id)
                if key in seen:
                    continue
                seen.add(key)
                values.append({
                    "event_id": event.event_id,
                    "provider": event.provider,
                    "calendar_id": event.calendar_id,
                    "title": event.title,
                    "description": event.description,
                    "location": event.location,
                    "start_time": event.start,
                    "end_time": event.end,
                    "timezone": event.timezone,
                    "all_day": event.all_day,
                    "attendees": event.attendees,
                    "visibility": event.visibility,
                    "source_provenance": event.source_provenance,
                })

            if not values:
                return 0

            logger.info(f"Inserting {len(values)} unique events (deduplicated from {len(events)})")

            # Batch inserts to avoid PostgreSQL's 32,767 argument limit
            # With 14 columns per row, ~2000 rows per batch is safe
            BATCH_SIZE = 2000
            total_inserted = 0

            for i in range(0, len(values), BATCH_SIZE):
                batch = values[i:i + BATCH_SIZE]

                # PostgreSQL UPSERT using INSERT ... ON CONFLICT DO UPDATE
                stmt = insert(CalendarEventDB).values(batch)
                stmt = stmt.on_conflict_do_update(
                    constraint="unique_provider_event",
                    set_={
                        "calendar_id": stmt.excluded.calendar_id,
                        "title": stmt.excluded.title,
                        "description": stmt.excluded.description,
                        "location": stmt.excluded.location,
                        "start_time": stmt.excluded.start_time,
                        "end_time": stmt.excluded.end_time,
                        "timezone": stmt.excluded.timezone,
                        "all_day": stmt.excluded.all_day,
                        "attendees": stmt.excluded.attendees,
                        "visibility": stmt.excluded.visibility,
                        "source_provenance": stmt.excluded.source_provenance,
                    }
                )

                await self.db_session.execute(stmt)
                total_inserted += len(batch)
                logger.debug(f"Inserted batch {i // BATCH_SIZE + 1}: {len(batch)} events")

            await self.db_session.commit()
            return total_inserted

        except Exception as e:
            logger.error(f"Failed to insert events to database: {e}", exc_info=True)
            # Rollback on error
            await self.db_session.rollback()
            return 0

    def _detect_provider(self, ics_url: str) -> Literal['google', 'm365']:
        """
        Detect calendar provider from URL.

        Args:
            ics_url: ICS feed URL

        Returns:
            Provider type ('google' or 'm365')
        """
        if 'google.com' in ics_url or 'calendar.google' in ics_url:
            return 'google'
        elif 'office365.com' in ics_url or 'outlook.office' in ics_url:
            return 'm365'
        else:
            # Default to google if cannot detect
            logger.warning(f"Could not detect provider from URL: {ics_url}, defaulting to google")
            return 'google'
