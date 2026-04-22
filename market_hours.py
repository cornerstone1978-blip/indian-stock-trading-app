"""Utility to check whether the Indian stock market is currently open."""

from datetime import datetime, time

import pytz

import config

IST = pytz.timezone(config.TIMEZONE)

MARKET_OPEN = time(config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE)
MARKET_CLOSE = time(config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE)

# Saturdays (5) and Sundays (6) — additional holidays need a calendar.
WEEKEND_DAYS = {5, 6}


def now_ist() -> datetime:
    return datetime.now(IST)


def is_market_open(dt: datetime | None = None) -> bool:
    """Return True if *dt* (or now) falls within NSE trading hours on a weekday."""
    if dt is None:
        dt = now_ist()
    else:
        dt = dt.astimezone(IST)

    if dt.weekday() in WEEKEND_DAYS:
        return False

    current_time = dt.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE
