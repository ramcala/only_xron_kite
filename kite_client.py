import logging
from config import KITE_ENABLE_REAL
try:
    from kiteconnect import KiteConnect
except Exception:
    KiteConnect = None

logger = logging.getLogger(__name__)


class KiteClientWrapper:
    """Wrapper that either calls real KiteConnect or simulates orders.

    Methods:
    - place_order: returns dict with order_id and status
    """

    def __init__(self, api_key: str, api_secret: str, access_token: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.kite = None

        if KITE_ENABLE_REAL:
            try:
                self.kite = KiteConnect(api_key=self.api_key)
                if access_token:
                    self.kite.set_access_token(access_token)
            except Exception as e:
                logger.exception("Failed to init KiteConnect: %s", e)

    def place_order(self, tradingsymbol: str, quantity: int, transaction_type: str):
        """Place a market order. transaction_type must be 'BUY' or 'SELL'.

        Returns: dict { 'order_id': str, 'status': 'success'|'error', 'raw': ... }
        """
        tx = transaction_type.upper()
        if tx not in ("BUY", "SELL"):
            return {"status": "error", "error": "transaction_type must be BUY or SELL"}

        if KITE_ENABLE_REAL and self.kite:
            try:
                order = self.kite.place_order(
                    variety="regular",
                    tradingsymbol=tradingsymbol,
                    exchange="NSE",
                    transaction_type=tx,
                    quantity=quantity,
                    order_type="MARKET",
                    product="CNC",
                )
                return {"status": "success", "order_id": str(order), "raw": order}
            except Exception as e:
                logger.exception("Kite place_order failed: %s", e)
                return {"status": "error", "error": str(e)}

        # Simulation mode
        logger.info("Simulating %s order for %s x%d", tx, tradingsymbol, quantity)
        fake_order_id = f"SIM-{tradingsymbol}-{tx}-{quantity}"
        return {"status": "success", "order_id": fake_order_id, "raw": {"simulated": True}}
