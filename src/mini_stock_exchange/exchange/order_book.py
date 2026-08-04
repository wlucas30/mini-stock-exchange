from .models import Instrument, Order, Price
from .order_queue import HeapOrderQueue, Side


class OrderBook:
    """Represents the entire order book for a single instrument."""

    def __init__(self, instrument: Instrument) -> None:
        self._instrument = instrument
        self._bids = HeapOrderQueue(Side.BUY)
        self._asks = HeapOrderQueue(Side.SELL)

    @property
    def best_bid(self) -> Order | None:
        return self._bids.peek()

    @property
    def best_ask(self) -> Order | None:
        return self._asks.peek()

    @property
    def best_bid_price(self) -> Price | None:
        order = self.best_bid
        return order.price_bps if order is not None else None

    @property
    def best_ask_price(self) -> Price | None:
        order = self.best_ask
        return order.price_bps if order is not None else None
