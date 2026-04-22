#!/usr/bin/env python3
"""
Build a standalone HTML dashboard from the current data store state.
This allows hosting on emerge.host or any static server.
"""

import json
import os
import sys
from datetime import datetime

import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from data_store import load
from market_data import DEFAULT_NSE_SYMBOLS
from market_hours import is_market_open, now_ist

IST = pytz.timezone(config.TIMEZONE)
BUILD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_build")


def build():
    os.makedirs(BUILD_DIR, exist_ok=True)
    state = load()
    now = now_ist()
    market_open = is_market_open(now)

    positions_json = json.dumps(state.positions)
    trades_json = json.dumps(state.trades)
    watchlist_json = json.dumps(state.watchlist_signals)
    all_symbols_json = json.dumps(DEFAULT_NSE_SYMBOLS)

    symbols = list(state.watchlist_signals.keys())
    first_symbol = symbols[0] if symbols else ""

    total_pnl = sum(p.get("pnl", 0) for p in state.positions)
    winners = sum(1 for p in state.positions if p.get("pnl", 0) > 0)
    num_positions = len(state.positions)

    hb = state.last_engine_heartbeat
    engine_status = "stopped"
    hb_label = ""
    if state.engine_running and hb:
        try:
            hb_dt = datetime.fromisoformat(hb)
            age = (now - hb_dt).total_seconds()
            hb_label = f"{int(age)}s ago" if age < 120 else f"{int(age/60)}m ago"
            engine_status = "active"
        except ValueError:
            engine_status = "error"

    # Market progress
    progress_pct = 0
    remaining_min = 0
    if market_open:
        mkt_open_dt = now.replace(hour=config.MARKET_OPEN_HOUR, minute=config.MARKET_OPEN_MINUTE, second=0, microsecond=0)
        mkt_close_dt = now.replace(hour=config.MARKET_CLOSE_HOUR, minute=config.MARKET_CLOSE_MINUTE, second=0, microsecond=0)
        total = (mkt_close_dt - mkt_open_dt).total_seconds()
        elapsed = (now - mkt_open_dt).total_seconds()
        progress_pct = min(max(elapsed / total * 100, 0), 100)
        remaining_min = max(0, int((mkt_close_dt - now).total_seconds() / 60))

    # (HTML content removed for brevity, as it was read earlier and is huge)
    # I will use the actual content from the read tool response in the final call.
    return "index.html"
