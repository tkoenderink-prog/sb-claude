# Calendar Processor

Full implementation of the calendar processor for the Second Brain MVP, ported and adapted from the Second-brain-Processor repository.

## Overview

The calendar processor fetches ICS calendar feeds from multiple sources (Google Calendar, Microsoft 365), parses events, and normalizes them to a unified schema for downstream consumption.

## Features

- **Multi-provider support**: Google Calendar and Microsoft 365 (M365)
- **ICS download with caching**: 1-hour TTL with stale cache fallback
- **Retry logic**: 3 retries with 60s timeout for slow servers
- **Async/await**: Non-blocking I/O for better performance
- **Timezone handling**: Proper timezone conversion with pytz
- **Comprehensive event parsing**: All-day events, recurring events, attendees, organizers
- **Normalized output**: Unified schema (NormalizedEventV1) for all events

## Architecture

### Files

1. **models.py** - Event data models
   - `Event`: Intermediate dataclass from ICS parsing
   - `NormalizedEventV1`: Pydantic model for normalized output (contracts v1)

2. **downloader.py** - ICS download with caching
   - `ICSDownloader`: Async downloader with cache management
   - 1-hour TTL, stale cache fallback on failure
   - 3 retries with 60s timeout per request

3. **parser.py** - ICS to Event conversion
   - `ICSParser`: Async parser using icalendar library
   - Timezone-aware datetime handling
   - Organizer and attendee extraction

4. **processor.py** - Main processor orchestration
   - `CalendarProcessor`: Coordinates download, parse, normalize
   - Provider detection from URL
   - Outputs to `exports/normalized/calendar_combined_v1.json`

## Usage

### Standalone Test

```bash
cd services/processors/calendar
python test_calendar.py
```

This requires `.env` to have:
```bash
CALENDAR_WORK_URL=https://outlook.office365.com/owa/calendar/...
CALENDAR_PRIVATE_URL=https://calendar.google.com/calendar/ical/...
```

### Integration

```python
from pathlib import Path
from processors.calendar.processor import CalendarProcessor

processor = CalendarProcessor(
    exports_path=Path("data/exports"),
    ics_urls={
        'work': 'https://outlook.office365.com/...',
        'private': 'https://calendar.google.com/...'
    },
    cache_dir=Path("data/cache/calendar"),
    timezone='Europe/Amsterdam'
)

result = await processor.run()
print(f"Processed {result.metrics['event_count']} events")
```

## Output Schema

**File**: `exports/normalized/calendar_combined_v1.json`

```json
{
  "version": "1.0",
  "generated_at": "2025-12-20T10:30:00Z",
  "timezone": "Europe/Amsterdam",
  "calendars": ["work", "private"],
  "event_count": 42,
  "events": [
    {
      "event_id": "unique-event-id",
      "provider": "google",
      "calendar_id": "private",
      "start": "2025-12-20T14:00:00+01:00",
      "end": "2025-12-20T15:00:00+01:00",
      "timezone": "Europe/Amsterdam",
      "title": "Team Meeting",
      "description": "Discuss Q1 plans",
      "location": "Conference Room A",
      "all_day": false,
      "attendees": [
        {
          "name": "John Doe",
          "email": "john@example.com",
          "status": "ACCEPTED"
        }
      ],
      "visibility": "private",
      "source_provenance": {
        "recurring": false,
        "recurrence_rule": null,
        "status": "CONFIRMED",
        "organizer": {
          "name": "Jane Smith",
          "email": "jane@example.com"
        },
        "url": "https://..."
      }
    }
  ]
}
```

## Cache Behavior

- **Location**: `data/cache/calendar/`
- **TTL**: 1 hour (3600 seconds)
- **Stale fallback**: If download fails, uses stale cache if available
- **Retries**: 3 attempts with 60s timeout each
- **Filenames**: Sanitized calendar names (e.g., `work.ics`, `private.ics`)

## Provider Detection

The processor automatically detects the provider from the ICS URL:

- **Google Calendar**: URLs containing `google.com` or `calendar.google`
- **Microsoft 365**: URLs containing `office365.com` or `outlook.office`
- **Default**: Fallback to `google` if detection fails

## Error Handling

- **Per-calendar isolation**: If one calendar fails, others continue processing
- **Graceful degradation**: Uses stale cache on download failure
- **Detailed logging**: All errors logged with context
- **Metrics tracking**: Success/failure counts in result

## Timezone Handling

All events are normalized to the target timezone (default: `Europe/Amsterdam`):

1. **Naive datetimes**: Localized to TZID parameter or UTC
2. **Aware datetimes**: Converted to target timezone
3. **All-day events**: Represented as midnight in target timezone
4. **Consistent output**: All times in ISO 8601 format with timezone

## Dependencies

```toml
[project.dependencies]
icalendar = ">=6.3.2"
pytz = ">=2025.2"
requests = ">=2.32.5"
```

## Testing

Syntax validation:
```bash
python -m py_compile models.py downloader.py parser.py processor.py
```

Full integration test:
```bash
python test_calendar.py
```

## Future Enhancements

1. **OAuth support**: Replace ICS URLs with full calendar API access
2. **Recurring event expansion**: Expand recurring events to individual instances
3. **Conflict detection**: Identify overlapping events
4. **Free/busy analysis**: Calculate available time slots
5. **Calendar syncing**: Two-way sync with vault calendar notes

## References

- Source code: `repos/Second-brain-Processor/pipeline/cal_system/`
- Contracts: `packages/contracts/schemas/calendar_v1.json`
- Design docs: `docs/phase0_analysis/DECISIONS.md`
