"""ICS Parser - Parse ICS calendar files into Event objects."""
import asyncio
from datetime import datetime, date, time, timedelta
from typing import Optional
import logging

from icalendar import Calendar
import pytz

from .models import Event

logger = logging.getLogger(__name__)


class ICSParser:
    """Parse ICS calendar files into Event objects (async wrapper)."""

    def __init__(self, timezone: str = "Europe/Amsterdam"):
        """
        Initialize parser with target timezone.

        Args:
            timezone: Target timezone for all events (default: Europe/Amsterdam)
        """
        self.target_tz = pytz.timezone(timezone)
        logger.info(f"ICSParser initialized with timezone: {timezone}")

    async def parse(self, ics_content: str, calendar_name: str) -> list[Event]:
        """
        Parse ICS content into Event objects (async).

        Args:
            ics_content: Raw ICS file content
            calendar_name: Name of the calendar (e.g., 'Private', 'Work')

        Returns:
            List of Event objects
        """
        # Run blocking parsing in thread pool
        loop = asyncio.get_event_loop()
        events = await loop.run_in_executor(
            None,
            self._parse_sync,
            ics_content,
            calendar_name
        )
        return events

    def _parse_sync(self, ics_content: str, calendar_name: str) -> list[Event]:
        """
        Synchronous parsing implementation.

        Args:
            ics_content: Raw ICS file content
            calendar_name: Name of the calendar

        Returns:
            List of Event objects
        """
        try:
            cal = Calendar.from_ical(ics_content)
            events = []

            for component in cal.walk('VEVENT'):
                try:
                    event = self._parse_event(component, calendar_name)
                    if event:
                        events.append(event)
                except Exception as e:
                    uid = component.get('UID', 'unknown')
                    logger.warning(f"Failed to parse event {uid}: {e}")
                    continue

            logger.info(f"Parsed {len(events)} events from {calendar_name}")
            return events

        except Exception as e:
            logger.error(f"Failed to parse calendar {calendar_name}: {e}")
            return []

    def _parse_event(self, vevent, calendar_name: str) -> Optional[Event]:
        """
        Parse a single VEVENT component.

        Args:
            vevent: icalendar VEVENT component
            calendar_name: Name of the calendar

        Returns:
            Event object or None if parsing fails
        """
        # Required fields
        uid = str(vevent.get('UID', ''))
        summary = str(vevent.get('SUMMARY', '(No title)'))

        if not uid:
            logger.warning("Event missing UID, skipping")
            return None

        # Parse start time (required)
        dtstart = vevent.get('DTSTART')
        if not dtstart:
            logger.warning(f"Event {uid} missing DTSTART, skipping")
            return None

        # Get TZID from DTSTART parameter if present
        dtstart_tzid = None
        if hasattr(dtstart, 'params'):
            dtstart_tzid = dtstart.params.get('TZID')

        start_dt = self._parse_datetime(dtstart.dt, dtstart_tzid)
        all_day = isinstance(dtstart.dt, date) and not isinstance(dtstart.dt, datetime)

        # Parse end time (use DTEND or DURATION, default to +1 hour)
        dtend = vevent.get('DTEND')
        duration = vevent.get('DURATION')

        if dtend:
            dtend_tzid = None
            if hasattr(dtend, 'params'):
                dtend_tzid = dtend.params.get('TZID')
            end_dt = self._parse_datetime(dtend.dt, dtend_tzid)
        elif duration:
            end_dt = start_dt + duration.dt
        else:
            # Default to 1 hour for regular events, full day for all-day events
            if all_day:
                end_dt = start_dt + timedelta(days=1)
            else:
                end_dt = start_dt + timedelta(hours=1)

        # Optional text fields
        description = str(vevent.get('DESCRIPTION', '')) if vevent.get('DESCRIPTION') else None
        location = str(vevent.get('LOCATION', '')) if vevent.get('LOCATION') else None
        status = str(vevent.get('STATUS', '')) if vevent.get('STATUS') else None
        transparency = str(vevent.get('TRANSP', '')) if vevent.get('TRANSP') else None
        url = str(vevent.get('URL', '')) if vevent.get('URL') else None

        # Recurrence fields
        rrule = vevent.get('RRULE')
        recurrence_rule = str(rrule.to_ical().decode('utf-8')) if rrule else None
        recurring = recurrence_rule is not None

        recurrence_id = vevent.get('RECURRENCE-ID')
        if recurrence_id:
            recurrence_id = str(recurrence_id.dt.isoformat())

        # People
        organizer = self._parse_organizer(vevent)
        attendees = self._parse_attendees(vevent)

        # Metadata
        created = vevent.get('CREATED')
        if created:
            created = self._parse_datetime(created.dt, None)

        last_modified = vevent.get('LAST-MODIFIED')
        if last_modified:
            last_modified = self._parse_datetime(last_modified.dt, None)

        sequence = int(vevent.get('SEQUENCE', 0))

        # Create Event object
        return Event(
            uid=uid,
            calendar=calendar_name,
            summary=summary,
            description=description,
            location=location,
            start=start_dt,
            end=end_dt,
            all_day=all_day,
            timezone=str(self.target_tz),
            recurring=recurring,
            recurrence_rule=recurrence_rule,
            recurrence_id=recurrence_id,
            status=status,
            transparency=transparency,
            organizer=organizer,
            attendees=attendees,
            url=url,
            created=created,
            last_modified=last_modified,
            sequence=sequence
        )

    def _parse_datetime(self, dt, tzid: Optional[str]) -> datetime:
        """
        Convert date/datetime to timezone-aware datetime in target timezone.

        Args:
            dt: date or datetime object
            tzid: Optional timezone ID from TZID parameter

        Returns:
            Timezone-aware datetime in target timezone
        """
        if isinstance(dt, datetime):
            # Handle datetime objects
            if dt.tzinfo is None:
                # Naive datetime - needs localization
                if tzid:
                    # Has explicit TZID parameter
                    try:
                        tz = pytz.timezone(tzid)
                        dt = tz.localize(dt)
                    except Exception as e:
                        logger.warning(f"Invalid TZID '{tzid}', assuming UTC: {e}")
                        dt = pytz.utc.localize(dt)
                else:
                    # No TZID - assume UTC
                    dt = pytz.utc.localize(dt)
            # Convert to target timezone
            return dt.astimezone(self.target_tz)

        elif isinstance(dt, date):
            # All-day event - create datetime at midnight in target timezone
            return self.target_tz.localize(datetime.combine(dt, time(0, 0)))

        else:
            raise ValueError(f"Unsupported datetime type: {type(dt)}")

    def _parse_organizer(self, vevent) -> Optional[dict[str, str]]:
        """
        Parse organizer information.

        Args:
            vevent: icalendar VEVENT component

        Returns:
            Dict with 'name' and 'email' keys, or None
        """
        organizer = vevent.get('ORGANIZER')
        if not organizer:
            return None

        result = {}

        # Extract email from mailto: URI
        email = str(organizer)
        if email.startswith('mailto:'):
            email = email[7:]
        result['email'] = email

        # Extract name from CN parameter
        if hasattr(organizer, 'params'):
            cn = organizer.params.get('CN')
            if cn:
                result['name'] = str(cn)
            else:
                result['name'] = email
        else:
            result['name'] = email

        return result

    def _parse_attendees(self, vevent) -> list[dict[str, str]]:
        """
        Parse attendee information.

        Args:
            vevent: icalendar VEVENT component

        Returns:
            List of dicts with 'name', 'email', and 'status' keys
        """
        attendees = vevent.get('ATTENDEE')
        if not attendees:
            return []

        # Handle single attendee vs multiple
        if not isinstance(attendees, list):
            attendees = [attendees]

        result = []
        for attendee in attendees:
            item = {}

            # Extract email from mailto: URI
            email = str(attendee)
            if email.startswith('mailto:'):
                email = email[7:]
            item['email'] = email

            # Extract parameters
            if hasattr(attendee, 'params'):
                # Name from CN parameter
                cn = attendee.params.get('CN')
                item['name'] = str(cn) if cn else email

                # Participation status
                partstat = attendee.params.get('PARTSTAT')
                item['status'] = str(partstat) if partstat else 'NEEDS-ACTION'
            else:
                item['name'] = email
                item['status'] = 'NEEDS-ACTION'

            result.append(item)

        return result
