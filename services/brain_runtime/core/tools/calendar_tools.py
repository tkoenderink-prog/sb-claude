"""Calendar tools wrapping the /calendar API."""

from datetime import datetime
import logging

from .registry import tool

logger = logging.getLogger(__name__)


@tool(
    name="get_today_events",
    description="Get calendar events for today from both Google and Microsoft 365 calendars. Returns events sorted by start time.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_today_events():
    """Get calendar events for today."""
    from api.calendar import get_today_events as api_get_today_events

    result = await api_get_today_events()
    return {
        "events": [event.model_dump() for event in result.events],
        "count": result.count,
        "date_range": result.date_range,
    }


@tool(
    name="get_week_events",
    description="Get calendar events for the next 7 days from both Google and Microsoft 365 calendars. Returns events sorted by start time.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def get_week_events():
    """Get calendar events for the next 7 days."""
    from api.calendar import get_week_events as api_get_week_events

    result = await api_get_week_events()
    return {
        "events": [event.model_dump() for event in result.events],
        "count": result.count,
        "date_range": result.date_range,
    }


@tool(
    name="get_events_in_range",
    description="Get calendar events within a custom date range. Returns events sorted by start time.",
    parameters={
        "type": "object",
        "properties": {
            "start": {
                "type": "string",
                "description": "Start date in ISO format (e.g., '2025-12-20T00:00:00')",
            },
            "end": {
                "type": "string",
                "description": "End date in ISO format (e.g., '2025-12-27T23:59:59')",
            },
        },
        "required": ["start", "end"],
    },
)
async def get_events_in_range(start: str, end: str):
    """Get calendar events within a date range."""
    from api.calendar import get_events_in_range as api_get_events_in_range

    # Parse ISO datetime strings
    start_dt = datetime.fromisoformat(start)
    end_dt = datetime.fromisoformat(end)

    result = await api_get_events_in_range(start=start_dt, end=end_dt)
    return {
        "events": [event.model_dump() for event in result.events],
        "count": result.count,
        "date_range": result.date_range,
    }


@tool(
    name="search_events",
    description="Search calendar events by title or description. Case-insensitive search across all events.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query to match against event titles and descriptions",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 20)",
                "default": 20,
            },
        },
        "required": ["query"],
    },
)
async def search_events(query: str, limit: int = 20):
    """Search calendar events by title or description."""
    from api.calendar import load_calendar_data

    data = load_calendar_data()
    query_lower = query.lower()

    # Search through events
    matches = []
    for event in data["events"]:
        title = event.get("title", "").lower()
        description = event.get("description", "").lower()

        if query_lower in title or query_lower in description:
            matches.append(event)

            if len(matches) >= limit:
                break

    # Sort by start time
    matches.sort(key=lambda e: e["start"])

    return {"query": query, "events": matches, "count": len(matches)}


def register_calendar_tools():
    """Register all calendar tools (called by decorator)."""
    # Tools are auto-registered by the @tool decorator
    logger.info("Calendar tools registered")
