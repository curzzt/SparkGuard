import re
from zoneinfo import ZoneInfo

from app.core.config import get_settings


def local_now(tz_name: str | None = None):
    tz = ZoneInfo(tz_name or get_settings().TIMEZONE)
    from datetime import datetime

    return datetime.now(tz)


def parse_time_hhmm(value: str):
    from datetime import time

    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError("invalid time format")
    hour, minute = int(parts[0]), int(parts[1])
    return time(hour, minute)


def format_time_hhmm(value) -> str:
    return value.strftime("%H:%M")
