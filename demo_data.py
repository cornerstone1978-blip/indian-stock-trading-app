"""
Generate demo / seed data for the dashboard.

Uses yfinance for real-time prices when available, with a fallback to
simulated data if the network call fails.
"""

from __future__ import annotations

import logging
import math
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List

import pytz

import config
from data_store import StoreState, TradeRecord, save, set_heartbeat, update_watchlist_signal
from strategy import Signal, calculate_stoploss, calculate_target, compute_sma

logger = logging.getLogger("trading.demo_data")

IST = pytz.timezone(config.TIMEZONE)

DEMO_WATCHLIST = {
    "RELIANCE":  {"token": 738561,  "exchange": "NSE"},
    "TCS":       {"token": 2953217, "exchange": "NSE"},
    "HDFCBANK":  {"token": 341249,  "exchange": "NSE"},
    "INFY":      {"token": 408065,  "exchange": "NSE"},
    "ICICIBANK": {"token": 1270529, "exchange": "NSE"},
}


def _generate_simulated_closes(base: float, n: int = 40) -> List[float]:
    """Fallback simulated closes when yfinance is unavailable."""
    closes = []
    price = base
    for i in range(n):
        trend = math.sin(i / 6) * base * 0.015
        noise = random.gauss(0, base * 0.005)
        price = base + trend + noise
        closes.append(round(price, 2))
    return closes


def _fetch_real_closes(symbol: str, exchange: str = "NSE") -> List[float]:
    """Fetch real historical closes via yfinance."""
    try:
        from market_data import fetch_historical_closes
        closes = fetch_historical_closes(symbol, exchange, period="3mo")
        if closes and len(closes) >= 5:
            return closes
    except Exception:
        logger.warning("yfinance fetch failed for %s, using simulated data", symbol)
    return []


def _get_current_price(symbol: str, exchange: str = "NSE") -> float | None:
    """Fetch current price from yfinance."""
    try:
        from market_data import fetch_current_price
        return fetch_current_price(symbol, exchange)
    except Exception:
        return None


# Fallback base prices in case yfinance is completely unavailable
_FALLBACK_BASES: Dict[str, float] = {
    "RELIANCE": 1360.0,
    "TCS": 3400.0,
    "HDFCBANK": 1900.0,
    "INFY": 1500.0,
    "ICICIBANK": 1350.0,
}


def generate_demo_state() -> StoreState:
    now = datetime.now(IST)

    trades: List[Dict[str, Any]] = []
    positions: List[Dict[str, Any]] = []
    watchlist_signals: Dict[str, Dict[str, Any]] = {}

    for symbol, info in DEMO_WATCHLIST.items():
        exchange = info.get("exchange", "NSE")

        # Try real data first, fall back to simulated
        closes = _fetch_real_closes(symbol, exchange)
        if not closes:
            base = _FALLBACK_BASES.get(symbol, 1000.0)
            random.seed(hash(symbol) % (2**31))
            closes = _generate_simulated_closes(base)

        sma = compute_sma(closes, config.SMA_PERIOD)
        current = closes[-1]
        prev = closes[-2] if len(closes) >= 2 else current
        prev_sma = compute_sma(closes[:-1], config.SMA_PERIOD)

        sig = "HOLD"
        if prev_sma and sma:
            if prev <= prev_sma and current > sma:
                sig = "BUY"
            elif prev >= prev_sma and current < sma:
                sig = "SELL"

        target = calculate_target(current) if sig == "BUY" else 0.0
        stoploss = calculate_stoploss(current) if sig == "BUY" else 0.0

        watchlist_signals[symbol] = {
            "signal": sig,
            "price": current,
            "sma": round(sma, 2) if sma else 0.0,
            "target": target,
            "stoploss": stoploss,
            "closes": closes,
            "timestamp": now.isoformat(),
        }

    # Build positions using real current prices
    position_symbols = ["INFY", "RELIANCE", "TCS"]
    for sym in position_symbols:
        if sym not in watchlist_signals:
            continue
        current_price = watchlist_signals[sym]["price"]
        # Simulated entry slightly different from current
        avg_price = round(current_price * random.uniform(0.98, 1.01), 2)
        qty = random.choice([3, 5, 10])
        positions.append({
            "tradingsymbol": sym,
            "exchange": "NSE",
            "quantity": qty,
            "average_price": avg_price,
            "last_price": current_price,
            "pnl": round((current_price - avg_price) * qty, 2),
            "product": random.choice(["CNC", "MIS"]),
        })

    # Historical trade log
    for i, sym in enumerate(list(DEMO_WATCHLIST.keys())[:4]):
        if sym not in watchlist_signals:
            continue
        entry = round(watchlist_signals[sym]["price"] * (1 - 0.005 * i), 2)
        trades.append({
            "symbol": sym,
            "signal": "BUY",
            "entry_price": entry,
            "target": calculate_target(entry),
            "stoploss": calculate_stoploss(entry),
            "quantity": (i + 1) * 3,
            "order_id": f"DEMO{100 + i}",
            "timestamp": (now - timedelta(hours=i + 1)).isoformat(),
            "status": "ACTIVE" if i < 2 else "CLOSED",
        })

    return StoreState(
        positions=positions,
        trades=trades,
        watchlist_signals=watchlist_signals,
        last_engine_heartbeat=now.isoformat(),
        engine_running=True,
    )


def seed_demo_data() -> None:
    state = generate_demo_state()
    save(state)


if __name__ == "__main__":
    seed_demo_data()
    print("Demo data seeded with real market prices.")
