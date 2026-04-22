"""Smoke test — ensure the dashboard module can be imported and key
functions / layouts are reachable without a running Streamlit server."""

import importlib
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import data_store


class TestDashboardDeps:
    """Validate that all dashboard dependencies are importable."""

    def test_import_plotly(self):
        import plotly.graph_objects as go
        assert go.Figure is not None

    def test_import_pandas(self):
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2, 3]})
        assert len(df) == 3

    def test_import_streamlit(self):
        import streamlit as st
        assert hasattr(st, "set_page_config")

    def test_import_data_store(self):
        assert hasattr(data_store, "load")
        assert hasattr(data_store, "save")

    def test_import_market_hours(self):
        from market_hours import is_market_open, now_ist
        assert callable(is_market_open)
        assert callable(now_ist)

    def test_import_strategy(self):
        from strategy import evaluate, compute_sma
        assert callable(evaluate)

    def test_import_market_data(self):
        from market_data import (
            fetch_current_price,
            fetch_historical_closes,
            search_symbols,
            get_yf_ticker,
            DEFAULT_NSE_SYMBOLS,
        )
        assert callable(fetch_current_price)
        assert callable(fetch_historical_closes)
        assert callable(search_symbols)
        assert callable(get_yf_ticker)
        assert len(DEFAULT_NSE_SYMBOLS) > 0

    def test_import_yfinance(self):
        import yfinance as yf
        assert hasattr(yf, "Ticker")

    def test_import_demo_data(self):
        from unittest.mock import patch
        with patch("demo_data._fetch_real_closes", return_value=[100.0] * 40):
            from demo_data import generate_demo_state
            state = generate_demo_state()
            assert len(state.watchlist_signals) > 0
