"""Provides implementations of the order priority queue, using an abstract base class
OrderQueue, which should implement price-time priority."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from .models import Order, OrderId, Side


class OrderQueue(ABC):
    """The abstract base class used for representing resting order priority queues."""

    def __init__(self, side: Side) -> None:
        self._side = side

    @property
    def side(self) -> Side:
        """The side of the order book this queue represents."""
        return self._side

    @abstractmethod
    def add(self, order: Order) -> None:
        """Adds an order to the queue.

        Parameters:
            order (Order): The order being added.

        """
        ...

    @abstractmethod
    def peek(self) -> Order | None:
        """Returns the highest-priority order without removing it."""
        ...

    @abstractmethod
    def pop(self) -> Order | None:
        """Remove and return the highest-priority order."""
        ...

    @abstractmethod
    def cancel(self, order_id: OrderId) -> Order | None:
        """Cancels the order with the given identifier and removes it from the queue.

        Returns None if the order was not found in the queue."""
        ...

    @abstractmethod
    def get(self, order_id: OrderId) -> Order | None:
        """Returns the order with the given identifier, if it is in the queue.

        Returns None if the order is not in the queue."""
        ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def __iter__(self) -> Iterator[Order]: ...

    def _higher_priority(self, order1: Order, order2: Order) -> bool:
        if order1.price_bps is None or order2.price_bps is None:
            raise ValueError("Resting orders must have a price")

        # Attempt to compare on price
        if order1.price_bps != order2.price_bps:
            if self.side is Side.BUY:
                return order1.price_bps > order2.price_bps
            return order1.price_bps < order2.price_bps

        # Cannot compare on price, fallback to time
        return order1.sequence < order2.sequence


class HeapOrderQueue(OrderQueue):
    """An OrderQueue represented using a heap data structure."""

    def __init__(self, side: Side) -> None:
        super().__init__(side)
        self._contents: list[Order] = []
        self._indices: dict[OrderId, int] = {}
        self._size = 0

    # HELPERS

    # Function to return the index of the parent of a given node
    def _parent(self, i: int) -> int:
        return (i - 1) // 2

    # Function to return the index of the left child of a given node
    def _left_child(self, i: int) -> int:
        return (2 * i) + 1

    # Function to return the index of the right child of a given node
    def _right_child(self, i: int) -> int:
        return (2 * i) + 2

    # Function to swap two orders at given indices
    def _swap(self, first: int, second: int) -> None:
        self._contents[first], self._contents[second] = (
            self._contents[second],
            self._contents[first],
        )
        self._indices[self._contents[first].order_id] = first
        self._indices[self._contents[second].order_id] = second

    # Function to shift up a node to maintain the heap property
    def _shift_up(self, i: int) -> None:
        while i > 0 and self._higher_priority(
            self._contents[i],
            self._contents[self._parent(i)],
        ):
            # Swap parent and current node
            self._swap(self._parent(i), i)

            # Change current node to parent and continue looping
            i = self._parent(i)

    # Function to shift down a node to maintain the heap property
    def _shift_down(self, i: int) -> None:
        # Get index of the highest priority child
        max_index = i

        left = self._left_child(i)
        right = self._right_child(i)

        if left < self._size and self._higher_priority(
            self._contents[left], self._contents[max_index]
        ):
            max_index = left

        if right < self._size and self._higher_priority(
            self._contents[right], self._contents[max_index]
        ):
            max_index = right

        # If not the same as i, restore the heap property
        if i != max_index:
            self._swap(i, max_index)
            self._shift_down(max_index)

    def _remove_at(self, index: int) -> Order:
        removed = self._contents[index]
        last_index = self._size - 1
        last = self._contents.pop()

        self._size -= 1
        del self._indices[removed.order_id]

        if index == last_index:
            return removed

        self._contents[index] = last
        self._indices[last.order_id] = index

        if index > 0 and self._higher_priority(
            self._contents[index], self._contents[self._parent(index)]
        ):
            self._shift_up(index)
        else:
            self._shift_down(index)

        return removed

    # PUBLIC FUNCS
    def add(self, order: Order) -> None:
        if order.order_id in self._indices:
            raise ValueError("Order ID already exists")
        if order.price_bps is None:
            raise ValueError("Resting orders must have a price")
        if not order.is_active:
            raise ValueError("Resting orders must be active")

        index = self._size
        self._contents.append(order)
        self._indices[order.order_id] = index
        self._size += 1
        self._shift_up(index)

    def peek(self) -> Order | None:
        if self._size == 0:
            return None
        return self._contents[0]

    def pop(self) -> Order | None:
        if self._size == 0:
            return None
        return self._remove_at(0)

    def cancel(self, order_id: OrderId) -> Order | None:
        index = self._indices.get(order_id)
        if index is None:
            return None

        result = self._remove_at(index)
        result.cancel()
        return result

    def get(self, order_id: OrderId) -> Order | None:
        index = self._indices.get(order_id)
        if index is None:
            return None
        return self._contents[index]

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterator[Order]:
        return iter(self._contents)

    def sorted_list(self) -> list[Order]:
        """Returns a list of orders sorted by priority decreasing."""

        def priority(order: Order) -> tuple[int, int]:
            if order.price_bps is None:
                raise RuntimeError("Resting order must have a price")

            price = -order.price_bps if self.side is Side.BUY else order.price_bps
            return price, order.sequence

        return sorted(self._contents, key=priority)
