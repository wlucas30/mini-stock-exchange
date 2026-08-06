from collections.abc import Callable
from dataclasses import dataclass

from .models import (
    Instrument,
    Order,
    OrderId,
    ParticipantId,
    PriceTicks,
    Quantity,
    Sequence,
    Symbol,
    Timestamp,
)
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

    @staticmethod
    def _snapshot_entry(order: Order) -> BookEntry:
        if order.price_ticks is None:
            raise RuntimeError("Resting order must have a price")

        return BookEntry(
            order_id=order.order_id,
            participant_id=order.participant_id,
            price_ticks=order.price_ticks,
            remaining_quantity=order.remaining_quantity,
            sequence=order.sequence,
            timestamp=order.timestamp,
        )

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

    def snapshot(self) -> BookSnapshot:
        return BookSnapshot(
            symbol=self._instrument.symbol,
            bids=tuple(
                self._snapshot_entry(order) for order in self._bids.sorted_list()
            ),
            asks=tuple(
                self._snapshot_entry(order) for order in self._asks.sorted_list()
            ),
        )


@dataclass(frozen=True, kw_only=True)
class BookEntry:
    order_id: OrderId
    participant_id: ParticipantId
    price_ticks: PriceTicks
    remaining_quantity: Quantity
    sequence: Sequence
    timestamp: Timestamp


@dataclass(frozen=True, kw_only=True)
class BookSnapshot:
    symbol: Symbol
    bids: tuple[BookEntry, ...]
    asks: tuple[BookEntry, ...]
