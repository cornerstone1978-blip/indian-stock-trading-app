import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch

import data_store
from demo_data import DEMO_WATCHLIST, generate_demo_state, seed_demo_data, _generate_simulated_closes


class TestDemoData:
    def setup_method(self):
        self._orig = data_store.STORE_PATH
        self._tmpdir = tempfile.mkdtemp()
        data_store.STORE_PATH = os.path.join(self._tmpdir, "test_store.json")

    def teardown_method(self):
        data_store.STORE_PATH = self._orig

    @patch("demo_data._fetch_real_closes")
    def test_generate_returns_store_state(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        assert isinstance(state, data_store.StoreState)

    @patch("demo_data._fetch_real_closes")
    def test_positions_populated(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        assert len(state.positions) >= 1

    @patch("demo_data._fetch_real_closes")
    def test_trades_populated(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        assert len(state.trades) >= 1

    @patch("demo_data._fetch_real_closes")
    def test_watchlist_has_all_symbols(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        for sym in DEMO_WATCHLIST:
            assert sym in state.watchlist_signals

    @patch("demo_data._fetch_real_closes")
    def test_watchlist_signal_has_closes(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        for sym, data in state.watchlist_signals.items():
            assert "closes" in data
            assert len(data["closes"]) > 0
            assert "signal" in data
            assert "price" in data

    @patch("demo_data._fetch_real_closes")
    def test_seed_writes_to_disk(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        seed_demo_data()
        assert os.path.exists(data_store.STORE_PATH)
        loaded = data_store.load()
        assert len(loaded.positions) >= 1

    @patch("demo_data._fetch_real_closes")
    def test_engine_running_flag(self, mock_fetch):
        mock_fetch.return_value = [100.0] * 40
        state = generate_demo_state()
        assert state.engine_running is True
        assert state.last_engine_heartbeat != ""

    def test_simulated_closes_fallback(self):
        closes = _generate_simulated_closes(1000.0, n=40)
        assert len(closes) == 40
        assert all(isinstance(c, float) for c in closes)
        assert all(c > 0 for c in closes)

    @patch("demo_data._fetch_real_closes")
    def test_fallback_to_simulated_on_empty(self, mock_fetch):
        mock_fetch.return_value = []
        state = generate_demo_state()
        # Should still generate data using simulated closes
        assert len(state.watchlist_signals) > 0
        for sym, data in state.watchlist_signals.items():
            assert len(data["closes"]) > 0
