from collections.abc import Callable

from .models import Instrument, Order, OrderId, PriceTicks
from .order_queue import HeapOrderQueue, OrderQueue, Side


def make_heap_order_queue(side: Side) -> OrderQueue:
    return HeapOrderQueue(side)


class OrderBook:
    """Represents the entire order book for a single instrument."""

    def __init__(
        self,
        instrument: Instrument,
        queue_factory: Callable[[Side], OrderQueue] = make_heap_order_queue,
    ) -> None:
        self._instrument = instrument
        self._bids = queue_factory(Side.BUY)
        self._asks = queue_factory(Side.SELL)

    @property
    def best_bid(self) -> Order | None:
        return self._bids.peek()

    @property
    def best_ask(self) -> Order | None:
        return self._asks.peek()

    @property
    def best_bid_price_ticks(self) -> PriceTicks | None:
        order = self.best_bid
        return order.price_ticks if order is not None else None

    @property
    def best_ask_price_ticks(self) -> PriceTicks | None:
        order = self.best_ask
        return order.price_ticks if order is not None else None

    def add_order(self, order: Order) -> None:
        """Adds an order to the relevant queue."""
        side = order.side
        queue = self._bids if side is Side.BUY else self._asks
        queue.add(order)

    def pop_best(self, side: Side) -> Order | None:
        """Removes and returns the order with highest priority from the given side."""
        queue = self._bids if side is Side.BUY else self._asks
        return queue.pop()

    def cancel_order(self, order_id: OrderId, side: Side) -> Order | None:
        """Cancels and removes an order from the relevant queue."""
        queue = self._bids if side is Side.BUY else self._asks
        return queue.cancel(order_id)

    def asks_by_priority(self) -> list[Order]:
        """Returns a list of asks ordered by priority decreasing."""
        return self._asks.sorted_list()
