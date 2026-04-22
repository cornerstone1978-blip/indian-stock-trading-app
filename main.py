#!/usr/bin/env python3
"""
Main loop for the Indian stock market trading application.

Runs continuously during market hours, evaluating the SMA crossover
strategy at a configurable polling interval and placing orders via
Zerodha Kite Connect.  Writes state to the shared data store so the
Streamlit dashboard can display it.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta

import pytz

import config
import data_store
from broker import Broker
from data_store import TradeRecord, set_heartbeat, update_positions, update_watchlist_signal
from logger import setup_logger
from market_hours import is_market_open, now_ist
from strategy import Signal, evaluate

logger = setup_logger("trading")

IST = pytz.timezone(config.TIMEZONE)

INSTRUMENT_TOKEN = 256265  # NIFTY 50 index (example)
TRADING_SYMBOL = "INFY"


def run_strategy_cycle(broker: Broker) -> None:
    now = now_ist()
    to_date = now.strftime("%Y-%m-%d")
    from_date = (now - timedelta(days=60)).strftime("%Y-%m-%d")

    try:
        closes = broker.fetch_historical(
            INSTRUMENT_TOKEN, from_date, to_date, interval="day",
        )
    except Exception:
        logger.exception("Failed to fetch historical data")
        return

    if not closes:
        logger.warning("No closing prices received — skipping cycle")
        return

    result = evaluate(closes)
    logger.info(
        "Strategy result: signal=%s price=%.2f sma=%.2f target=%.2f sl=%.2f",
        result.signal.value, result.price, result.sma,
        result.target, result.stoploss,
    )

    # Publish signal to data store for the dashboard
    update_watchlist_signal(TRADING_SYMBOL, {
        "signal": result.signal.value,
        "price": result.price,
        "sma": result.sma,
        "target": result.target,
        "stoploss": result.stoploss,
        "closes": closes,
        "timestamp": now.isoformat(),
    })

    if result.signal == Signal.BUY:
        try:
            order_id = broker.place_order(
                tradingsymbol=TRADING_SYMBOL,
                transaction_type="BUY",
                quantity=config.DEFAULT_QUANTITY,
            )
            logger.info(
                "BUY executed — order_id=%s target=%.2f stoploss=%.2f",
                order_id, result.target, result.stoploss,
            )
            data_store.add_trade(TradeRecord(
                symbol=TRADING_SYMBOL,
                signal="BUY",
                entry_price=result.price,
                target=result.target,
                stoploss=result.stoploss,
                quantity=config.DEFAULT_QUANTITY,
                order_id=order_id,
                timestamp=now.isoformat(),
            ))
        except Exception:
            logger.exception("BUY order failed")

    elif result.signal == Signal.SELL:
        try:
            order_id = broker.place_order(
                tradingsymbol=TRADING_SYMBOL,
                transaction_type="SELL",
                quantity=config.DEFAULT_QUANTITY,
            )
            logger.info("SELL executed — order_id=%s", order_id)
            data_store.add_trade(TradeRecord(
                symbol=TRADING_SYMBOL,
                signal="SELL",
                entry_price=result.price,
                target=0.0,
                stoploss=0.0,
                quantity=config.DEFAULT_QUANTITY,
                order_id=order_id,
                timestamp=now.isoformat(),
            ))
        except Exception:
            logger.exception("SELL order failed")

    # Sync positions from broker
    try:
        positions = broker.get_positions()
        net = positions.get("net", [])
        update_positions(net)
    except Exception:
        logger.exception("Failed to sync positions")


def main() -> None:
    logger.info("=== Indian Trading App started ===")
    logger.info(
        "Timezone: %s | Market hours: %02d:%02d – %02d:%02d",
        config.TIMEZONE,
        config.MARKET_OPEN_HOUR, config.MARKET_OPEN_MINUTE,
        config.MARKET_CLOSE_HOUR, config.MARKET_CLOSE_MINUTE,
    )

    broker = Broker()

    while True:
        now = now_ist()
        set_heartbeat(running=True)

        if is_market_open(now):
            logger.info("Market is OPEN — running strategy cycle")
            run_strategy_cycle(broker)
        else:
            logger.debug(
                "Market CLOSED at %s — sleeping", now.strftime("%H:%M:%S"),
            )

        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        set_heartbeat(running=False)
        logger.info("Shutting down gracefully")
        sys.exit(0)
