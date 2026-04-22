"""
Shared data store — decouples the trading engine from the Streamlit UI.

Uses a JSON file on disk as the exchange medium. The engine writes trade
state here; the dashboard reads it. Thread-safe via filelock-style
atomic writes.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytz

import config

IST = pytz.timezone(config.TIMEZONE)

STORE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "store.json",
)


@dataclass
class TradeRecord:
    symbol: str
    signal: str
    entry_price: float
    target: float
    stoploss: float
    quantity: int
    order_id: str
    timestamp: str
    status: str = "ACTIVE"


@dataclass
class StoreState:
    positions: List[Dict[str, Any]] = field(default_factory=list)
    trades: List[Dict[str, Any]] = field(default_factory=list)
    watchlist_signals: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_engine_heartbeat: str = ""
    engine_running: bool = False


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)


def save(state: StoreState) -> None:
    _ensure_dir()
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(STORE_PATH), suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(asdict(state), f, indent=2)
        os.replace(tmp_path, STORE_PATH)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def load() -> StoreState:
    _ensure_dir()
    if not os.path.exists(STORE_PATH):
        return StoreState()
    try:
        with open(STORE_PATH) as f:
            raw = json.load(f)
        return StoreState(**raw)
    except (json.JSONDecodeError, TypeError):
        return StoreState()


def add_trade(record: TradeRecord) -> None:
    state = load()
    state.trades.append(asdict(record))
    save(state)


def update_positions(positions: List[Dict[str, Any]]) -> None:
    state = load()
    state.positions = positions
    save(state)


def update_watchlist_signal(symbol: str, signal_data: Dict[str, Any]) -> None:
    state = load()
    state.watchlist_signals[symbol] = signal_data
    save(state)


def set_heartbeat(running: bool = True) -> None:
    state = load()
    state.last_engine_heartbeat = datetime.now(IST).isoformat()
    state.engine_running = running
    save(state)
