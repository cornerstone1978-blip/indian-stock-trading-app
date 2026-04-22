import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config
from strategy import Signal, StrategyResult, calculate_stoploss, calculate_target, compute_sma, evaluate


class TestComputeSMA:
    def test_exact_period(self):
        closes = list(range(1, 21))  # 1..20
        sma = compute_sma(closes, period=20)
        assert sma == 10.5

    def test_longer_than_period(self):
        closes = [10.0] * 25
        assert compute_sma(closes, period=20) == 10.0

    def test_shorter_than_period_returns_none(self):
        closes = [1.0, 2.0, 3.0]
        assert compute_sma(closes, period=20) is None

    def test_single_element_period_1(self):
        assert compute_sma([42.0], period=1) == 42.0

    def test_uses_last_n_values(self):
        closes = [100.0] * 10 + [200.0] * 20
        sma = compute_sma(closes, period=20)
        assert sma == 200.0


class TestTargetStoploss:
    def test_target_default(self):
        assert calculate_target(100.0) == 102.0

    def test_stoploss_default(self):
        assert calculate_stoploss(100.0) == 99.0

    def test_target_custom_pct(self):
        assert calculate_target(200.0, pct=5.0) == 210.0

    def test_stoploss_custom_pct(self):
        assert calculate_stoploss(200.0, pct=5.0) == 190.0

    def test_rounding(self):
        result = calculate_target(33.33, pct=3.0)
        assert result == 34.33


class TestEvaluate:
    def test_insufficient_data_returns_hold(self):
        closes = [100.0] * config.SMA_PERIOD  # exactly SMA_PERIOD, need +1
        result = evaluate(closes)
        assert result.signal == Signal.HOLD

    def test_buy_signal_on_crossover(self):
        # Build closes where prev_close <= prev_sma and current_close > current_sma
        period = config.SMA_PERIOD
        # First `period` values at 100, then one at 99 (below SMA), then one at 105 (above SMA)
        base = [100.0] * period
        base.append(99.0)   # prev_close, still keeps sma ~100
        base.append(105.0)  # current_close crosses above
        result = evaluate(base)
        assert result.signal == Signal.BUY
        assert result.target > 0
        assert result.stoploss > 0

    def test_sell_signal_on_crossover(self):
        period = config.SMA_PERIOD
        base = [100.0] * period
        base.append(101.0)  # prev above sma
        base.append(95.0)   # current below sma
        result = evaluate(base)
        assert result.signal == Signal.SELL
        assert result.target == 0.0
        assert result.stoploss == 0.0

    def test_hold_when_no_crossover(self):
        period = config.SMA_PERIOD
        # All above SMA → no crossover
        base = [100.0] * period
        base.append(101.0)
        base.append(102.0)
        result = evaluate(base)
        assert result.signal == Signal.HOLD

    def test_empty_closes(self):
        result = evaluate([])
        assert result.signal == Signal.HOLD
        assert result.price == 0.0

    def test_result_is_strategy_result(self):
        period = config.SMA_PERIOD
        closes = [100.0] * (period + 1)
        result = evaluate(closes)
        assert isinstance(result, StrategyResult)
