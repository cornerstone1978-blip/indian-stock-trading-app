import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import data_store
from data_store import StoreState, TradeRecord, add_trade, load, save, set_heartbeat, update_positions, update_watchlist_signal


class TestStoreState:
    def test_defaults(self):
        s = StoreState()
        assert s.positions == []
        assert s.trades == []
        assert s.watchlist_signals == {}
        assert s.last_engine_heartbeat == ""
        assert s.engine_running is False


class TestSaveLoad:
    def setup_method(self):
        self._orig = data_store.STORE_PATH
        self._tmpdir = tempfile.mkdtemp()
        data_store.STORE_PATH = os.path.join(self._tmpdir, "test_store.json")

    def teardown_method(self):
        data_store.STORE_PATH = self._orig

    def test_save_then_load_roundtrip(self):
        state = StoreState(positions=[{"symbol": "INFY"}], engine_running=True)
        save(state)
        loaded = load()
        assert loaded.positions == [{"symbol": "INFY"}]
        assert loaded.engine_running is True

    def test_load_missing_file_returns_defaults(self):
        loaded = load()
        assert loaded.positions == []

    def test_load_corrupt_file_returns_defaults(self):
        os.makedirs(os.path.dirname(data_store.STORE_PATH), exist_ok=True)
        with open(data_store.STORE_PATH, "w") as f:
            f.write("{{{bad json")
        loaded = load()
        assert loaded.positions == []

    def test_add_trade(self):
        rec = TradeRecord(
            symbol="TCS", signal="BUY", entry_price=3400.0,
            target=3468.0, stoploss=3366.0, quantity=5,
            order_id="ORD1", timestamp="2026-04-22T10:00:00",
        )
        add_trade(rec)
        state = load()
        assert len(state.trades) == 1
        assert state.trades[0]["symbol"] == "TCS"
        assert state.trades[0]["status"] == "ACTIVE"

    def test_update_positions(self):
        update_positions([{"symbol": "A"}, {"symbol": "B"}])
        state = load()
        assert len(state.positions) == 2

    def test_update_watchlist_signal(self):
        update_watchlist_signal("INFY", {"signal": "BUY", "price": 1450.0})
        state = load()
        assert "INFY" in state.watchlist_signals
        assert state.watchlist_signals["INFY"]["signal"] == "BUY"

    def test_set_heartbeat(self):
        set_heartbeat(running=True)
        state = load()
        assert state.engine_running is True
        assert state.last_engine_heartbeat != ""

    def test_multiple_trades_accumulate(self):
        for i in range(3):
            rec = TradeRecord(
                symbol=f"SYM{i}", signal="BUY", entry_price=100.0 + i,
                target=102.0, stoploss=99.0, quantity=1,
                order_id=f"ORD{i}", timestamp="2026-04-22T10:00:00",
            )
            add_trade(rec)
        state = load()
        assert len(state.trades) == 3

    def test_atomic_write_leaves_no_tmp_on_success(self):
        save(StoreState())
        tmp_files = [f for f in os.listdir(os.path.dirname(data_store.STORE_PATH)) if f.endswith(".tmp")]
        assert tmp_files == []
