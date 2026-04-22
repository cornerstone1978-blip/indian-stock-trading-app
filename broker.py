"""
Broker integration layer for Zerodha Kite Connect.

Wraps kiteconnect SDK calls behind a clean interface so the rest of the
application never imports kiteconnect directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from kiteconnect import KiteConnect

import config

logger = logging.getLogger("trading.broker")


class Broker:
    def __init__(
        self,
        api_key: str = config.API_KEY,
        access_token: str = config.ACCESS_TOKEN,
    ):
        self.kite = KiteConnect(api_key=api_key)
        if access_token:
            self.kite.set_access_token(access_token)
        logger.info("Broker initialised (api_key=%s…)", api_key[:4] if api_key else "N/A")

    # ------------------------------------------------------------------
    # Historical data
    # ------------------------------------------------------------------
    def fetch_historical(
        self,
        instrument_token: int,
        from_date: str,
        to_date: str,
        interval: str = "day",
    ) -> List[float]:
        """Return a list of closing prices for the given instrument."""
        data = self.kite.historical_data(
            instrument_token, from_date, to_date, interval,
        )
        closes = [float(candle["close"]) for candle in data]
        logger.debug(
            "Fetched %d candles for token %s (%s → %s)",
            len(closes), instrument_token, from_date, to_date,
        )
        return closes

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------
    def place_order(
        self,
        tradingsymbol: str,
        transaction_type: str,
        quantity: int = config.DEFAULT_QUANTITY,
        price: Optional[float] = None,
        order_type: str = "MARKET",
        product: str = config.PRODUCT_TYPE,
        exchange: str = config.EXCHANGE,
    ) -> str:
        """Place an order and return the order ID."""
        params: Dict[str, Any] = {
            "tradingsymbol": tradingsymbol,
            "exchange": exchange,
            "transaction_type": transaction_type,
            "quantity": quantity,
            "order_type": order_type,
            "product": product,
            "variety": "regular",
        }
        if price is not None and order_type == "LIMIT":
            params["price"] = price

        order_id = self.kite.place_order(**params)
        logger.info(
            "Order placed: %s %s %d x %s @ %s → order_id=%s",
            transaction_type, tradingsymbol, quantity,
            order_type, price or "MKT", order_id,
        )
        return order_id

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
    ) -> str:
        """Modify an existing order."""
        params: Dict[str, Any] = {"variety": "regular", "order_id": order_id}
        if quantity is not None:
            params["quantity"] = quantity
        if price is not None:
            params["price"] = price
        if order_type is not None:
            params["order_type"] = order_type

        modified_id = self.kite.modify_order(**params)
        logger.info("Order modified: order_id=%s → %s", order_id, modified_id)
        return modified_id

    def cancel_order(self, order_id: str) -> str:
        cancelled_id = self.kite.cancel_order(variety="regular", order_id=order_id)
        logger.info("Order cancelled: order_id=%s", cancelled_id)
        return cancelled_id

    def get_positions(self) -> Dict[str, Any]:
        return self.kite.positions()

    def get_orders(self) -> List[Dict[str, Any]]:
        return self.kite.orders()
