import pytest

from mini_stock_exchange.exchange.models import (
    Order,
    OrderStatus,
    OrderType,
    Side,
)
from mini_stock_exchange.exchange.order_queue import HeapOrderQueue


# Helper function to make a dummy order for testing
def make_order(
    order_id: int,
    price: int | None,
    sequence: int,
    status: OrderStatus = OrderStatus.OPEN,
) -> Order:
    return Order(
        order_id=order_id,
        sequence=sequence,
        participant_id=f"participant-{order_id}",
        symbol="AAPL",
        order_type=OrderType.LIMIT,
        original_quantity=10,
        remaining_quantity=10,
        timestamp=sequence,
        price_bps=price,
        status=status,
    )


def test_empty_queue() -> None:
    queue = HeapOrderQueue(Side.BUY)

    assert len(queue) == 0
    assert queue.peek() is None
    assert queue.pop() is None
    assert queue.get(1) is None
    assert queue.cancel(1) is None


@pytest.mark.parametrize(
    ("side", "prices"),
    [
        (Side.BUY, [103, 102, 101]),
        (Side.SELL, [101, 102, 103]),
    ],
)
def test_pop_uses_price_time_priority(side: Side, prices: list[int]) -> None:
    queue = HeapOrderQueue(side)
    orders = [
        make_order(1, price=102, sequence=1),
        make_order(2, price=101, sequence=2),
        make_order(3, price=103, sequence=3),
    ]
    for order in orders:
        queue.add(order)

    for i in range(len(prices)):
        result = queue.pop()
        assert result is not None
        assert result.price_bps == prices[i]

    assert len(queue) == 0


def test_equal_prices_use_sequence_priority() -> None:
    queue = HeapOrderQueue(Side.BUY)
    later = make_order(1, price=100, sequence=2)
    earlier = make_order(2, price=100, sequence=1)

    queue.add(later)
    queue.add(earlier)

    assert queue.pop() is earlier
    assert queue.pop() is later


def test_get_follows_orders_after_heap_swaps() -> None:
    queue = HeapOrderQueue(Side.BUY)
    low = make_order(1, price=100, sequence=1)
    high = make_order(2, price=110, sequence=2)

    queue.add(low)
    queue.add(high)

    assert queue.get(low.order_id) is low
    assert queue.get(high.order_id) is high


def test_cancel_removes_order_and_restores_heap() -> None:
    queue = HeapOrderQueue(Side.BUY)
    orders = [
        make_order(1, price=110, sequence=1),
        make_order(2, price=105, sequence=2),
        make_order(3, price=108, sequence=3),
        make_order(4, price=100, sequence=4),
    ]
    for order in orders:
        queue.add(order)

    cancelled = queue.cancel(2)

    assert cancelled is orders[1]
    assert cancelled is not None
    assert cancelled.status is OrderStatus.CANCELLED
    assert queue.get(2) is None
    assert len(queue) == 3
    assert [queue.pop().order_id for _ in range(3)] == [1, 3, 4]  # type: ignore[union-attr]


def test_duplicate_order_id_is_rejected() -> None:
    queue = HeapOrderQueue(Side.BUY)
    queue.add(make_order(1, price=100, sequence=1))

    with pytest.raises(ValueError, match="Order ID already exists"):
        queue.add(make_order(1, price=101, sequence=2))
