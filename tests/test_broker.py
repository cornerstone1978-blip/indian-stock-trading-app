import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import MagicMock, patch

import config
from broker import Broker


class TestBroker:
    @patch("broker.KiteConnect")
    def setup_method(self, method, mock_kite_cls):
        self.mock_kite = MagicMock()
        mock_kite_cls.return_value = self.mock_kite
        self.broker = Broker(api_key="test_key", access_token="test_token")

    def test_init_sets_access_token(self):
        self.mock_kite.set_access_token.assert_called_once_with("test_token")

    def test_fetch_historical_returns_closes(self):
        self.mock_kite.historical_data.return_value = [
            {"close": 100.0, "open": 99.0},
            {"close": 101.0, "open": 100.0},
            {"close": 102.0, "open": 101.0},
        ]
        closes = self.broker.fetch_historical(256265, "2026-01-01", "2026-03-01")
        assert closes == [100.0, 101.0, 102.0]
        self.mock_kite.historical_data.assert_called_once()

    def test_place_order_market(self):
        self.mock_kite.place_order.return_value = "ORD123"
        order_id = self.broker.place_order(
            tradingsymbol="INFY",
            transaction_type="BUY",
            quantity=5,
        )
        assert order_id == "ORD123"
        call_kwargs = self.mock_kite.place_order.call_args[1]
        assert call_kwargs["tradingsymbol"] == "INFY"
        assert call_kwargs["transaction_type"] == "BUY"
        assert call_kwargs["quantity"] == 5
        assert call_kwargs["order_type"] == "MARKET"
        assert call_kwargs["exchange"] == config.EXCHANGE

    def test_place_order_limit_includes_price(self):
        self.mock_kite.place_order.return_value = "ORD456"
        self.broker.place_order(
            tradingsymbol="RELIANCE",
            transaction_type="BUY",
            price=2500.0,
            order_type="LIMIT",
        )
        call_kwargs = self.mock_kite.place_order.call_args[1]
        assert call_kwargs["price"] == 2500.0
        assert call_kwargs["order_type"] == "LIMIT"

    def test_modify_order(self):
        self.mock_kite.modify_order.return_value = "MOD789"
        result = self.broker.modify_order("ORD123", quantity=10, price=105.0)
        assert result == "MOD789"
        call_kwargs = self.mock_kite.modify_order.call_args[1]
        assert call_kwargs["order_id"] == "ORD123"
        assert call_kwargs["quantity"] == 10
        assert call_kwargs["price"] == 105.0

    def test_cancel_order(self):
        self.mock_kite.cancel_order.return_value = "CAN101"
        result = self.broker.cancel_order("ORD123")
        assert result == "CAN101"

    def test_get_positions(self):
        self.mock_kite.positions.return_value = {"net": [], "day": []}
        assert self.broker.get_positions() == {"net": [], "day": []}

    def test_get_orders(self):
        self.mock_kite.orders.return_value = [{"order_id": "1"}]
        assert self.broker.get_orders() == [{"order_id": "1"}]
