"""Calendar event models for processing and normalization."""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel


@dataclass
class Event:
    """Intermediate event data structure from ICS parsing."""
    # Core fields
    uid: str
    calendar: str
    summary: str
    description: Optional[str]
    location: Optional[str]

    # Time fields (timezone-aware)
    start: datetime
    end: datetime
    all_day: bool
    timezone: str

    # Recurrence fields
    recurring: bool
    recurrence_rule: Optional[str]
    recurrence_id: Optional[str]

    # Status fields
    status: Optional[str]
    transparency: Optional[str]

    # People fields
    organizer: Optional[dict[str, str]]  # {name, email}
    attendees: list[dict[str, str]]  # [{name, email, status}]

    # Metadata fields
    url: Optional[str]
    created: Optional[datetime]
    last_modified: Optional[datetime]
    sequence: int

    # Calculated fields (will be set by expander/analyzer)
    duration_minutes: int = 0
    is_past: bool = False
    is_today: bool = False
    is_this_week: bool = False
    days_until: int = 0

    # Obsidian integration
    obsidian_link: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON export."""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        for key in ['start', 'end', 'created', 'last_modified']:
            if result.get(key):
                result[key] = result[key].isoformat()
        return result


class NormalizedEventV1(BaseModel):
    """Normalized calendar event matching contracts schema v1."""
    event_id: str
    provider: Literal['google', 'm365']
    calendar_id: str
    start: datetime
    end: datetime
    timezone: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    all_day: bool
    attendees: list[dict[str, str]] = []
    visibility: Literal['private', 'public'] = 'private'
    source_provenance: dict = {}

    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    @classmethod
    def from_event(cls, event: Event, provider: Literal['google', 'm365']) -> 'NormalizedEventV1':
        """
        Convert Event dataclass to NormalizedEventV1.

        Args:
            event: Event dataclass from ICS parsing
            provider: Provider type (google or m365)

        Returns:
            NormalizedEventV1 instance
        """
        return cls(
            event_id=event.uid,
            provider=provider,
            calendar_id=event.calendar,
            start=event.start,
            end=event.end,
            timezone=event.timezone,
            title=event.summary,
            description=event.description,
            location=event.location,
            all_day=event.all_day,
            attendees=event.attendees,
            visibility='private',  # Default to private, can be enhanced later
            source_provenance={
                'recurring': event.recurring,
                'recurrence_rule': event.recurrence_rule,
                'recurrence_id': event.recurrence_id,
                'status': event.status,
                'transparency': event.transparency,
                'organizer': event.organizer,
                'url': event.url,
                'created': event.created.isoformat() if event.created else None,
                'last_modified': event.last_modified.isoformat() if event.last_modified else None,
                'sequence': event.sequence
            }
        )
