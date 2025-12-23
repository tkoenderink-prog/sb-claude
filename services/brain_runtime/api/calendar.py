"""Calendar query endpoints."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import pytz

router = APIRouter(prefix="/calendar", tags=["calendar"])

# Path to calendar data
app_root = Path(__file__).parent.parent.parent.parent
calendar_data_path = app_root / "exports" / "normalized" / "calendar_combined_v1.json"


class CalendarEvent(BaseModel):
    """Calendar event for API response."""

    event_id: str
    provider: str
    calendar_id: str
    start: datetime
    end: datetime
    timezone: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: bool


class CalendarResponse(BaseModel):
    """Response with calendar events."""

    events: list[CalendarEvent]
    count: int
    date_range: dict[str, str]


def load_calendar_data() -> dict:
    """Load calendar data from JSON file."""
    if not calendar_data_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Calendar data not found. Run the calendar processor first.",
        )

    try:
        with open(calendar_data_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to parse calendar data: {e}"
        )


def filter_events_by_date_range(
    events: list[dict], start_date: datetime, end_date: datetime
) -> list[dict]:
    """Filter events to those within a date range."""
    # Ensure start/end dates are timezone-aware
    if start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    filtered = []
    for event in events:
        event_start = datetime.fromisoformat(event["start"])
        event_end = datetime.fromisoformat(event["end"])

        # Include if event overlaps with date range
        if event_start < end_date and event_end > start_date:
            filtered.append(event)

    # Sort by start time
    filtered.sort(key=lambda e: e["start"])
    return filtered


@router.get("/today", response_model=CalendarResponse)
async def get_today_events():
    """
    Get calendar events for today.

    Returns events that occur today, sorted by start time.
    """
    data = load_calendar_data()

    # Get today's date range in local timezone (Europe/Amsterdam)
    local_tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.now(local_tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    events = filter_events_by_date_range(data["events"], today_start, today_end)

    return CalendarResponse(
        events=[CalendarEvent(**e) for e in events],
        count=len(events),
        date_range={"start": today_start.isoformat(), "end": today_end.isoformat()},
    )


@router.get("/week", response_model=CalendarResponse)
async def get_week_events():
    """
    Get calendar events for the next 7 days.

    Returns events that occur in the next 7 days, sorted by start time.
    """
    data = load_calendar_data()

    # Get next 7 days date range in local timezone
    local_tz = pytz.timezone("Europe/Amsterdam")
    now = datetime.now(local_tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    events = filter_events_by_date_range(data["events"], start, end)

    return CalendarResponse(
        events=[CalendarEvent(**e) for e in events],
        count=len(events),
        date_range={"start": start.isoformat(), "end": end.isoformat()},
    )


@router.get("/range", response_model=CalendarResponse)
async def get_events_in_range(start: datetime, end: datetime):
    """
    Get calendar events within a custom date range.

    Args:
        start: Start of date range (ISO format)
        end: End of date range (ISO format)

    Returns events that occur in the range, sorted by start time.
    """
    if end <= start:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    data = load_calendar_data()
    events = filter_events_by_date_range(data["events"], start, end)

    return CalendarResponse(
        events=[CalendarEvent(**e) for e in events],
        count=len(events),
        date_range={"start": start.isoformat(), "end": end.isoformat()},
    )


@router.get("/status")
async def get_calendar_status():
    """Get status of calendar data."""
    if not calendar_data_path.exists():
        return {
            "available": False,
            "message": "Calendar data not found. Run the calendar processor.",
        }

    try:
        data = load_calendar_data()
        return {
            "available": True,
            "version": data.get("version"),
            "generated_at": data.get("generated_at"),
            "timezone": data.get("timezone"),
            "calendars": data.get("calendars", []),
            "event_count": data.get("event_count", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
