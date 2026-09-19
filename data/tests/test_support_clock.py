"""Unit tests for Application Clock and timezone handling."""
# Craft Framework
# Copyright (c) 2026 Antonio Santos <snarthost@gmail.com>
# Licensed under the MIT License. See LICENSE in the project root.

from datetime import datetime
from zoneinfo import ZoneInfo

from engine.support import clock


def test_clock_timezone_defaults_to_valid_zoneinfo():
    """Verify timezone returns a valid tzinfo even if config is uninitialized."""
    tz = clock.timezone()
    assert isinstance(tz, ZoneInfo)


def test_clock_now_and_now_naive():
    """Verify clock.now() is aware and clock.now_naive() is timezone-free."""
    now_aware = clock.now()
    now_naive = clock.now_naive()

    assert now_aware.tzinfo is not None
    assert now_naive.tzinfo is None
    # Difference should be under 1 second
    assert abs((now_aware.replace(tzinfo=None) - now_naive).total_seconds()) < 1.0


def test_clock_today():
    """Verify clock.today() returns a date matching clock.now()."""
    today = clock.today()
    assert today == clock.now().date()


def test_clock_formatting():
    """Verify format_datetime and format_date return expected string format."""
    dt = datetime(2026, 9, 16, 15, 30, 45, tzinfo=ZoneInfo("UTC"))
    formatted_dt = clock.format_datetime(dt)
    formatted_d = clock.format_date(dt)

    assert "2026" in formatted_dt
    assert "2026-09-16" == formatted_d
