"""
Real-time market data fetcher using yfinance.

Provides functions to fetch current prices, historical closes, and
search for NSE/BSE stock symbols. Replaces simulated demo data with
actual market values.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytz
import yfinance as yf

import config

logger = logging.getLogger("trading.market_data")

IST = pytz.timezone(config.TIMEZONE)

# Popular NSE stocks for default watchlist / search suggestions
DEFAULT_NSE_SYMBOLS: List[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "AXISBANK", "BAJFINANCE", "MARUTI", "TITAN",
    "SUNPHARMA", "HCLTECH", "WIPRO", "ASIANPAINT", "ULTRACEMCO",
    "NESTLEIND", "TATAMOTORS", "TATASTEEL", "POWERGRID", "NTPC",
    "ADANIENT", "ADANIPORTS", "ONGC", "JSWSTEEL", "TECHM",
    "BAJAJFINSV", "INDUSINDBK", "COALINDIA", "GRASIM", "CIPLA",
    "DRREDDY", "EICHERMOT", "APOLLOHOSP", "DIVISLAB", "BPCL",
    "BRITANNIA", "HEROMOTOCO", "M&M", "SBILIFE", "HDFCLIFE",
    "TATACONSUM", "DABUR", "VEDL", "ZOMATO", "PAYTM",
]


def get_yf_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert a bare symbol to a yfinance-compatible ticker.

    NSE stocks get `.NS` suffix, BSE stocks get `.BO`.
    If the symbol already has a suffix, return as-is.
    """
    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        return symbol
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    return f"{symbol}{suffix}"


def fetch_current_price(symbol: str, exchange: str = "NSE") -> Optional[float]:
    """Fetch the latest price for a given symbol via yfinance."""
    yf_symbol = get_yf_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(yf_symbol)
        fi = ticker.fast_info
        price = fi.get("lastPrice") or fi.get("regularMarketPrice")
        if price and price > 0:
            return round(float(price), 2)
        # Fallback: last close from history
        hist = ticker.history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
    except Exception:
        logger.warning("Failed to fetch price for %s", yf_symbol, exc_info=True)
    return None


def fetch_historical_closes(
    symbol: str,
    exchange: str = "NSE",
    period: str = "3mo",
) -> List[float]:
    """Fetch historical daily closing prices from yfinance.

    Returns a list of float closing prices (oldest → newest).
    """
    yf_symbol = get_yf_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning("No history returned for %s", yf_symbol)
            return []
        closes = [round(float(c), 2) for c in hist["Close"].tolist()]
        return closes
    except Exception:
        logger.warning("Failed to fetch history for %s", yf_symbol, exc_info=True)
        return []


def fetch_stock_info(symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
    """Fetch basic stock info (name, sector, etc.)."""
    yf_symbol = get_yf_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info or {}
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "exchange": exchange,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "yf_ticker": yf_symbol,
        }
    except Exception:
        logger.warning("Failed to fetch info for %s", yf_symbol, exc_info=True)
        return {"symbol": symbol, "name": symbol, "exchange": exchange}


def search_symbols(query: str) -> List[str]:
    """Search for symbols matching the query from the default list.

    Simple prefix/substring matching against the curated NSE symbols list.
    Returns up to 20 matches, sorted alphabetically.
    """
    if not query or not query.strip():
        return DEFAULT_NSE_SYMBOLS[:20]
    q = query.strip().upper()
    matches = [s for s in DEFAULT_NSE_SYMBOLS if q in s]
    # Also accept exact input as a potential custom symbol
    if q not in matches and len(q) >= 2:
        matches.insert(0, q)
    return matches[:20]


def fetch_watchlist_data(
    symbols: List[str],
    exchange: str = "NSE",
    sma_period: int = config.SMA_PERIOD,
    target_pct: float = config.DEFAULT_TARGET_PCT,
    stoploss_pct: float = config.DEFAULT_STOPLOSS_PCT,
) -> Dict[str, Dict[str, Any]]:
    """Fetch real-time watchlist data for multiple symbols.

    Returns a dict of {symbol: signal_data} ready for the data store.
    """
    from strategy import calculate_stoploss, calculate_target, compute_sma

    now = datetime.now(IST)
    watchlist_signals: Dict[str, Dict[str, Any]] = {}

    for symbol in symbols:
        closes = fetch_historical_closes(symbol, exchange, period="3mo")
        if not closes or len(closes) < 2:
            continue

        current = closes[-1]
        prev = closes[-2]
        sma = compute_sma(closes, sma_period)
        prev_sma = compute_sma(closes[:-1], sma_period)

        sig = "HOLD"
        if prev_sma and sma:
            if prev <= prev_sma and current > sma:
                sig = "BUY"
            elif prev >= prev_sma and current < sma:
                sig = "SELL"

        target = calculate_target(current, target_pct) if sig == "BUY" else 0.0
        stoploss = calculate_stoploss(current, stoploss_pct) if sig == "BUY" else 0.0

        watchlist_signals[symbol] = {
            "signal": sig,
            "price": current,
            "sma": round(sma, 2) if sma else 0.0,
            "target": target,
            "stoploss": stoploss,
            "closes": closes,
            "timestamp": now.isoformat(),
        }

    return watchlist_signals
