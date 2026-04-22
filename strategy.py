"""
Simple 20-period SMA crossover strategy.

Signal logic:
- BUY when the latest close crosses ABOVE the 20-period SMA.
- SELL when the latest close crosses BELOW the 20-period SMA.
- HOLD otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

import config


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class StrategyResult:
    signal: Signal
    price: float
    sma: float
    target: float
    stoploss: float


def compute_sma(closes: List[float], period: int = config.SMA_PERIOD) -> float | None:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def calculate_target(buy_price: float, pct: float = config.DEFAULT_TARGET_PCT) -> float:
    return round(buy_price * (1 + pct / 100), 2)


def calculate_stoploss(buy_price: float, pct: float = config.DEFAULT_STOPLOSS_PCT) -> float:
    return round(buy_price * (1 - pct / 100), 2)


def evaluate(closes: List[float]) -> StrategyResult:
    """Evaluate the SMA crossover strategy on a list of closing prices.

    Requires at least ``SMA_PERIOD + 1`` data points so that we can compare
    the previous bar's relationship to the SMA with the current bar's.
    """
    period = config.SMA_PERIOD
    if len(closes) < period + 1:
        return StrategyResult(
            signal=Signal.HOLD,
            price=closes[-1] if closes else 0.0,
            sma=0.0,
            target=0.0,
            stoploss=0.0,
        )

    current_sma = compute_sma(closes, period)
    prev_sma = compute_sma(closes[:-1], period)

    current_close = closes[-1]
    prev_close = closes[-2]

    signal = Signal.HOLD

    # Crossover detection
    if prev_close <= prev_sma and current_close > current_sma:
        signal = Signal.BUY
    elif prev_close >= prev_sma and current_close < current_sma:
        signal = Signal.SELL

    target = calculate_target(current_close) if signal == Signal.BUY else 0.0
    stoploss = calculate_stoploss(current_close) if signal == Signal.BUY else 0.0

    return StrategyResult(
        signal=signal,
        price=current_close,
        sma=round(current_sma, 2),
        target=target,
        stoploss=stoploss,
    )
