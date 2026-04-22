"""Tests for market_data module — yfinance integration."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

import config
from market_data import (
    DEFAULT_NSE_SYMBOLS,
    fetch_current_price,
    fetch_historical_closes,
    fetch_watchlist_data,
    get_yf_ticker,
    search_symbols,
)


class TestGetYfTicker:
    def test_nse_suffix(self):
        assert get_yf_ticker("RELIANCE", "NSE") == "RELIANCE.NS"

    def test_bse_suffix(self):
        assert get_yf_ticker("RELIANCE", "BSE") == "RELIANCE.BO"

    def test_already_has_ns_suffix(self):
        assert get_yf_ticker("RELIANCE.NS") == "RELIANCE.NS"

    def test_already_has_bo_suffix(self):
        assert get_yf_ticker("RELIANCE.BO", "NSE") == "RELIANCE.BO"

    def test_default_exchange_is_nse(self):
        assert get_yf_ticker("TCS") == "TCS.NS"

    def test_case_insensitive_exchange(self):
        assert get_yf_ticker("INFY", "nse") == "INFY.NS"
        assert get_yf_ticker("INFY", "bse") == "INFY.BO"


class TestSearchSymbols:
    def test_empty_query_returns_top_20(self):
        result = search_symbols("")
        assert len(result) == 20
        assert result == DEFAULT_NSE_SYMBOLS[:20]

    def test_whitespace_query(self):
        result = search_symbols("   ")
        assert len(result) == 20

    def test_exact_match(self):
        result = search_symbols("RELIANCE")
        assert "RELIANCE" in result

    def test_partial_match(self):
        result = search_symbols("INF")
        assert "INFY" in result

    def test_case_insensitive(self):
        result = search_symbols("reliance")
        assert "RELIANCE" in result

    def test_custom_symbol_added(self):
        result = search_symbols("XYZCORP")
        assert "XYZCORP" in result

    def test_max_20_results(self):
        result = search_symbols("A")
        assert len(result) <= 20

    def test_single_char_no_custom(self):
        result = search_symbols("A")
        # Single char should not be added as custom (len < 2 check)
        # But 'A' is length 1 so it shouldn't be added as custom
        assert all(s in DEFAULT_NSE_SYMBOLS or len(s) > 1 for s in result)


class TestFetchCurrentPrice:
    @patch("market_data.yf.Ticker")
    def test_returns_price_from_fast_info(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"lastPrice": 1450.55}
        mock_ticker_cls.return_value = mock_ticker

        price = fetch_current_price("INFY", "NSE")
        assert price == 1450.55
        mock_ticker_cls.assert_called_once_with("INFY.NS")

    @patch("market_data.yf.Ticker")
    def test_fallback_to_history(self, mock_ticker_cls):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {}
        mock_hist = pd.DataFrame({"Close": [1400.0, 1420.0, 1450.0]})
        mock_ticker.history.return_value = mock_hist
        mock_ticker_cls.return_value = mock_ticker

        price = fetch_current_price("INFY")
        assert price == 1450.0

    @patch("market_data.yf.Ticker")
    def test_returns_none_on_error(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("Network error")
        price = fetch_current_price("BADSTOCK")
        assert price is None

    @patch("market_data.yf.Ticker")
    def test_bse_suffix(self, mock_ticker_cls):
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {"lastPrice": 2500.0}
        mock_ticker_cls.return_value = mock_ticker

        fetch_current_price("RELIANCE", "BSE")
        mock_ticker_cls.assert_called_once_with("RELIANCE.BO")


class TestFetchHistoricalCloses:
    @patch("market_data.yf.Ticker")
    def test_returns_closes(self, mock_ticker_cls):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_hist = pd.DataFrame({"Close": [100.0, 101.0, 102.0, 103.0, 104.0]})
        mock_ticker.history.return_value = mock_hist
        mock_ticker_cls.return_value = mock_ticker

        closes = fetch_historical_closes("TCS", "NSE")
        assert closes == [100.0, 101.0, 102.0, 103.0, 104.0]

    @patch("market_data.yf.Ticker")
    def test_empty_history(self, mock_ticker_cls):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_cls.return_value = mock_ticker

        closes = fetch_historical_closes("BADSTOCK")
        assert closes == []

    @patch("market_data.yf.Ticker")
    def test_network_error(self, mock_ticker_cls):
        mock_ticker_cls.side_effect = Exception("Timeout")
        closes = fetch_historical_closes("INFY")
        assert closes == []


class TestFetchWatchlistData:
    @patch("market_data.fetch_historical_closes")
    def test_returns_signal_data(self, mock_closes):
        # 40 data points with the last one crossing above SMA
        base = [100.0] * 38
        base.append(99.0)  # prev below sma
        base.append(105.0)  # current above sma (BUY crossover)
        mock_closes.return_value = base

        result = fetch_watchlist_data(["TESTSTOCK"], sma_period=20)
        assert "TESTSTOCK" in result
        data = result["TESTSTOCK"]
        assert "signal" in data
        assert "price" in data
        assert "sma" in data
        assert "closes" in data
        assert data["price"] == 105.0

    @patch("market_data.fetch_historical_closes")
    def test_skips_empty_data(self, mock_closes):
        mock_closes.return_value = []
        result = fetch_watchlist_data(["NODATA"])
        assert "NODATA" not in result

    @patch("market_data.fetch_historical_closes")
    def test_multiple_symbols(self, mock_closes):
        mock_closes.return_value = [100.0] * 40
        result = fetch_watchlist_data(["A", "B", "C"])
        assert len(result) == 3
