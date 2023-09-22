import pandas
from datetime import datetime
import recurring_ical_events
from dateutil.relativedelta import relativedelta
import icalendar


class CalendarEvent:

    @staticmethod
    def from_dict(event: dict):
        def validate_datetime_str(datetime_str: str) -> bool:
            try:
                datetime.fromisoformat(datetime_str)
                return True
            except ValueError:
                return False

        validation_rules = {
            "uid": lambda value: type(value) == str,
            "start": lambda value: type(value) == str and validate_datetime_str(value),
            "end": lambda value: type(value) == str and validate_datetime_str(value),
            "created": lambda value: type(value) == str and validate_datetime_str(value),
            "summary": lambda value: type(value) == str,
            "description": lambda value: type(value) == str,
            "location": lambda value: type(value) == str,
            "rrule": lambda value: type(value) == str,
            "status": lambda value: type(value) == str,
        }

        error_message: str = "dict can not be converted to CalendarEvent."
        for key in validation_rules.keys():
            if key not in event.keys():
                raise ValueError(f"{error_message} Missing key: {key}")
            if not validation_rules[key](event[key]):
                raise ValueError(
                    f"{error_message} Validation failed for key: {key}"
                )

        return CalendarEvent(
            uid=event["uid"],
            start=datetime.fromisoformat(event["start"]),
            end=datetime.fromisoformat(event["end"]),
            created=datetime.fromisoformat(event["created"]),
            summary=event["summary"],
            description=event["description"],
            location=event["location"],
            rrule=event["rrule"],
            status=event["status"],
        )

    @staticmethod
    def from_ical_component(event: icalendar.cal.Component):
        try:
            description: str = str(event["DESCRIPTION"])
        except KeyError:
            description: str = ""
        try:
            location: str = str(event["LOCATION"])
        except KeyError:
            location: str = ""
        try:
            rrule: str = event["RRULE"].to_ical().decode("utf-8")
        except Exception:
            rrule: str = ""
        try:
            status: str = str(event["STATUS"])
        except KeyError:
            status: str = ""
        return CalendarEvent(
            start=event["DTSTART"].dt,
            end=event["DTEND"].dt,
            created=event["CREATED"].dt,
            uid=str(event["UID"]),
            summary=str(event["SUMMARY"]),
            description=description,
            location=location,
            rrule=rrule,
            status=status
        )

    def __init__(
            self, uid: str, start: datetime, end: datetime, created: datetime,
            summary: str, description: str, location: str, rrule: str, status: str
    ):
        self.uid = uid
        self.start: datetime = start
        self.end: datetime = end
        self.duration: pandas.Timedelta = pandas.Timedelta(end - start)
        self.created: datetime = created
        self.summary: str = summary
        self.description: str = description
        self.location: str = location
        self.rrule: str = rrule
        self.status: str = status

    def __eq__(self, other):
        return all([
            self.uid == other.uid,
            self.start == other.start,
            self.end == other.end,
            self.created == other.created,
            self.summary == other.summary,
            self.description == other.description,
            self.location == other.location,
            self.rrule == other.rrule,
            self.status == other.status
        ])

    def to_dict(self):
        return {
            "uid": self.uid,
            "start": str(self.start.isoformat()),
            "end": str(self.end.isoformat()),
            "duration": str(self.duration.isoformat()),
            "created": str(self.created.isoformat()),
            "name": self.summary,
            "summary": self.summary,
            "description": self.description,
            "location": self.location,
            "rrule": self.rrule,
            "status": self.status
        }


class Calendar:

    @staticmethod
    def from_ical(ical_string: str):
        calendar_icalendar: icalendar.Calendar = icalendar.Calendar.from_ical(ical_string)
        properties: dict = dict(calendar_icalendar)
        cal_start: datetime = datetime.now()
        cal_end: datetime = cal_start + relativedelta(months=3)
        return Calendar(
            events=[
                CalendarEvent.from_ical_component(event) for event in calendar_icalendar.walk("vevent")
            ],
            recurring_events=[
                CalendarEvent.from_ical_component(event) for event in recurring_ical_events.of(calendar_icalendar)
                .between(cal_start, cal_end)
            ],
            prod_id=str(properties["PRODID"]),
            version=str(properties["VERSION"]),
            scale=str(properties["CALSCALE"]),
            timezone=str(properties["X-WR-TIMEZONE"]),
            name=str(properties["X-WR-CALNAME"]),
            description=str(properties["X-WR-CALDESC"])
        )

    def __init__(
            self, events: [CalendarEvent], recurring_events: [CalendarEvent], prod_id: str, version: str, scale: str,
            name: str, timezone: str, description: str
    ):
        self.events: [CalendarEvent] = events
        self.recurring_events: [CalendarEvent] = recurring_events
        self.prod_id: str = prod_id
        self.version: str = version
        self.scale: str = scale
        self.name: str = name
        self.timezone: str = timezone
        self.description: str = description

        self.events.sort(key=lambda event: event.start)
        self.recurring_events.sort(key=lambda event: event.start)

    def to_dict(self) -> dict:
        return {
            "prod_id": self.prod_id,
            "version": self.version,
            "scale": self.scale,
            "timezone": self.timezone,
            "name": self.name,
            "description": self.description,
            "events": [event.to_dict() for event in self.events],
            "recurring_events": [event.to_dict() for event in self.recurring_events],
        }
