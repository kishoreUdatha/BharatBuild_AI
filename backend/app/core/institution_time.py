"""
The institution's clock.

Containers run UTC and the database stores naive UTC, but a college runs on
local wall-clock time: "today" is today in Coimbatore, and a review at 10:00 is
10:00 there. India is UTC+5:30, so after 18:30 local the two disagree about the
date - which is how taking evening attendance came to be refused as "a day that
has not happened".

Anything that reasons about a time a person named, or about "today" as a person
experiences it, goes through here. Everything stored stays naive UTC, which is
what the rest of the codebase already assumes.
"""

from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.logging_config import logger


def zone() -> Optional[ZoneInfo]:
    """The configured zone, or None when it cannot be loaded."""
    try:
        return ZoneInfo(settings.INSTITUTION_TIMEZONE)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning(f"[Time] Unknown timezone {settings.INSTITUTION_TIMEZONE!r}; "
                       "falling back to the server clock")
        return None


def local_now() -> datetime:
    """Now, as a local wall clock reads it (timezone-aware)."""
    tz = zone()
    return datetime.now(tz) if tz else datetime.now()


def local_today() -> date:
    """Today where the institution is, not where the server is."""
    return local_now().date()


def to_utc(local: datetime) -> datetime:
    """
    A local wall-clock time as the naive UTC the database stores.

    A value that already carries an offset is trusted and converted; a naive
    one is read as institution-local, because that is what a person typing
    into a form means.
    """
    tz = zone()
    if local.tzinfo is None:
        if tz is None:
            return local
        local = local.replace(tzinfo=tz)
    return local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def to_local(utc_naive: datetime) -> datetime:
    """Naive UTC back to a local wall clock, for anything rendered server-side."""
    tz = zone()
    aware = utc_naive.replace(tzinfo=ZoneInfo("UTC"))
    return aware.astimezone(tz) if tz else aware.replace(tzinfo=None)


def utc_now() -> datetime:
    """Naive UTC now, matching how timestamps are stored."""
    return datetime.utcnow()


def combine_local(day: date, at: time) -> datetime:
    """A local date and time, stored as naive UTC."""
    return to_utc(datetime.combine(day, at))


def parse_local_time(raw: str) -> time:
    """A HH:MM (or HH:MM:SS) wall-clock time."""
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw.strip(), fmt).time()
        except (ValueError, AttributeError):
            continue
    raise ValueError("Give a time like 10:30.")


def parse_local_date(raw: str) -> date:
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError("Give a date like %s." % local_today().isoformat())


def humanise(utc_naive: Optional[datetime]) -> Optional[str]:
    """A stored timestamp, written the way the institution would say it."""
    if utc_naive is None:
        return None
    return to_local(utc_naive).strftime("%d %b %Y, %I:%M %p").replace(" 0", " ")


__all__ = [
    "combine_local", "humanise", "local_now", "local_today", "parse_local_date",
    "parse_local_time", "timedelta", "to_local", "to_utc", "utc_now", "zone",
]


# ---------------------------------------------------------------- sessions

# The college day, as the timetable runs it. Marking is not blocked outside
# these - a trainer who takes the register at 17:00 still needs to record it -
# but they are what "the current session" means and what the screen defaults to.
SESSION_WINDOWS = {
    "forenoon": (time(9, 30), time(12, 30)),
    "afternoon": (time(13, 30), time(16, 30)),
}


def session_window(session: str):
    """Start and end of a session, as local wall-clock times."""
    return SESSION_WINDOWS[session]


def current_session(now: Optional[datetime] = None) -> Optional[str]:
    """
    Which session the clock is inside, or None between and outside them.

    Used to preselect, never to refuse: lunchtime and the evening are when a
    trainer catches up on a register they could not take at the time.
    """
    clock = (now or local_now()).time()
    for name, (start, end) in SESSION_WINDOWS.items():
        if start <= clock <= end:
            return name
    return None


def nearest_session(now: Optional[datetime] = None) -> str:
    """
    The session a trainer most likely means right now.

    Inside a window it is that one. Before the afternoon starts the morning is
    still the one being caught up on; after it, the afternoon.
    """
    inside = current_session(now)
    if inside:
        return inside
    clock = (now or local_now()).time()
    return "forenoon" if clock < SESSION_WINDOWS["afternoon"][0] else "afternoon"
