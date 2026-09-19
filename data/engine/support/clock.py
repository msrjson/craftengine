"""Application clock — the single source of truth for time and timezones.

Why this exists:
Discrepancies between system wall clock, UTC container clock, and application timezone
can cause scheduled jobs, database timestamps, and user displays to drift apart.

This module unifies time handling across the framework by consulting the application's
configured `APP_TIMEZONE` (defaults to 'UTC').

Key functions:
- `clock.now()`: Timezone-aware datetime in application timezone.
- `clock.now_naive()`: Local wall-clock datetime without tzinfo (for timestamp columns in SQL).
- `clock.today()`: Current `date` in the application timezone.
- `clock.to_app_tz(dt)`: Convert any datetime to the application timezone.

Category: Core Framework (Support).
Relations:
  - Used across ORM, scheduler, audit logs, and controllers.
"""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from __future__ import annotations

from datetime import date, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

__all__ = [
    "timezone_name",
    "timezone",
    "now",
    "now_naive",
    "today",
    "to_app_tz",
    "format_datetime",
    "format_date",
    "DATE_FORMAT",
    "DATETIME_FORMAT",
]

DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

_FALLBACK = "UTC"


def timezone_name() -> str:
    """Return the configured application timezone name (`app.APP_TIMEZONE`).

    Late import: config is loaded after bootstrap, and the clock module must not
    depend on early bootstrap ordering.
    """
    try:
        from engine.container.application import Container

        app = Container.getInstance()
        config = app.make("config")
        tz = config.get("app.APP_TIMEZONE") or config.get("app.timezone")
        return str(tz) if tz else _FALLBACK
    except Exception:
        return _FALLBACK


def timezone() -> tzinfo:
    """Return the `ZoneInfo` of the configured application timezone.

    An invalid or unknown timezone falls back gracefully to UTC rather than
    crashing the entire request or database write.
    """
    try:
        return ZoneInfo(timezone_name())
    except ZoneInfoNotFoundError, ValueError, KeyError:
        return ZoneInfo(_FALLBACK)


def now() -> datetime:
    """Return the current timezone-aware datetime in the application's timezone."""
    return datetime.now(timezone())


def now_naive() -> datetime:
    """Return current wall-clock time without tzinfo, suitable for database storage.

    Database columns are standard TIMESTAMP without timezone; storing naive wall-clock
    time prevents cross-database driver interpretation mismatches between SQLite
    and PostgreSQL.
    """
    return now().replace(tzinfo=None)


def today() -> date:
    """Return today's date in the application timezone."""
    return now().date()


def to_app_tz(value: datetime, assume_utc: bool = False) -> datetime:
    """Convert an arbitrary datetime to the application timezone.

    If `assume_utc` is True and `value` is naive, it is assumed to be UTC before conversion.
    Otherwise naive values are assumed to already be in the application timezone.
    """
    if value.tzinfo is None:
        source_tz = ZoneInfo(_FALLBACK) if assume_utc else timezone()
        value = value.replace(tzinfo=source_tz)
    return value.astimezone(timezone())


def format_datetime(value: datetime | None = None, fmt: str = DATETIME_FORMAT) -> str:
    """Format datetime as string in the application timezone."""
    target = to_app_tz(value) if value is not None else now()
    return target.strftime(fmt)


def format_date(value: date | datetime | None = None, fmt: str = DATE_FORMAT) -> str:
    """Format date as string in the application timezone."""
    if value is None:
        return today().strftime(fmt)
    if isinstance(value, datetime):
        return to_app_tz(value).date().strftime(fmt)
    return value.strftime(fmt)
