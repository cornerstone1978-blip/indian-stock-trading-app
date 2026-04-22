import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime

import pytz

from market_hours import MARKET_CLOSE, MARKET_OPEN, is_market_open

IST = pytz.timezone("Asia/Kolkata")


class TestIsMarketOpen:
    def _make_dt(self, year, month, day, hour, minute):
        return IST.localize(datetime(year, month, day, hour, minute))

    def test_open_during_market_hours_weekday(self):
        dt = self._make_dt(2026, 4, 22, 10, 0)
        assert is_market_open(dt) is True

    def test_open_at_exactly_market_open(self):
        dt = self._make_dt(2026, 4, 22, 9, 15)
        assert is_market_open(dt) is True

    def test_open_at_exactly_market_close(self):
        dt = self._make_dt(2026, 4, 22, 15, 30)
        assert is_market_open(dt) is True

    def test_closed_before_market_open(self):
        dt = self._make_dt(2026, 4, 22, 9, 14)
        assert is_market_open(dt) is False

    def test_closed_after_market_close(self):
        dt = self._make_dt(2026, 4, 22, 15, 31)
        assert is_market_open(dt) is False

    def test_closed_on_saturday(self):
        # 25 Apr 2026 is Saturday
        dt = self._make_dt(2026, 4, 25, 10, 0)
        assert dt.weekday() == 5
        assert is_market_open(dt) is False

    def test_closed_on_sunday(self):
        # 26 Apr 2026 is Sunday
        dt = self._make_dt(2026, 4, 26, 10, 0)
        assert dt.weekday() == 6
        assert is_market_open(dt) is False

    def test_utc_datetime_converted(self):
        # 10:00 IST = 04:30 UTC → should be open
        utc = pytz.utc.localize(datetime(2026, 4, 22, 4, 30))
        assert is_market_open(utc) is True

    def test_midnight_closed(self):
        dt = self._make_dt(2026, 4, 22, 0, 0)
        assert is_market_open(dt) is False
