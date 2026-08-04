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
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[Order]:
        ...


class HeapOrderQueue(OrderQueue):
    """An OrderQueue represented using a heap data structure."""

    def __init__(self, side: Side) -> None:
        super().__init__(side)

    def add(self, order: Order) -> None:
        ...

    def peek(self) -> Order | None:
        ...

    def pop(self) -> Order | None:
        ...

    def cancel(self, order_id: OrderId) -> Order | None:
        ...

    def get(self, order_id: OrderId) -> Order | None:
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[Order]:
        ...
