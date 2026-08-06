from collections.abc import Callable

from .models import (
    Cash,
    Instrument,
    Order,
    OrderId,
    OrderStatus,
    OrderType,
    Participant,
    ParticipantId,
    Quantity,
    RequestForOrder,
    Sequence,
    Side,
    Symbol,
    Timestamp,
    Trade,
    TradeId,
)
from .order_book import BookSnapshot, OrderBook


class Exchange:
    def __init__(self, time: Callable[[], Timestamp]) -> None:
        self._time = time

        self._instruments: dict[Symbol, Instrument] = {}
        self._order_books: dict[Symbol, OrderBook] = {}
        self._participants: dict[ParticipantId, Participant] = {}

        self._orders: dict[OrderId, Order] = {}
        self._active_orders: dict[OrderId, Order] = {}
        self._trades: list[Trade] = []
        self._reserved_cash: dict[OrderId, Cash] = {}
        self._reserved_positions: dict[OrderId, Quantity] = {}

        self._next_order_id: OrderId = 1
        self._next_trade_id: TradeId = 1
        self._next_sequence_number: Sequence = 1

    def _generate_order_id(self) -> OrderId:
        order_id = self._next_order_id
        self._next_order_id += 1
        return order_id

    def _generate_trade_id(self) -> TradeId:
        trade_id = self._next_trade_id
        self._next_trade_id += 1
        return trade_id

    def _generate_sequence_number(self) -> Sequence:
        sequence_number = self._next_sequence_number
        self._next_sequence_number += 1
        return sequence_number

    def _get_market_buy_cost(self, symbol: Symbol, quantity: Quantity) -> Cash:
        """Return the cash needed to consume currently available asks."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        book = self._order_books.get(symbol)
        if book is None:
            raise ValueError(f"Symbol {symbol} does not exist")

        remaining = quantity
        required_cash: Cash = 0

        for order in book.asks_by_priority():
            assert order.price_ticks is not None

            fill_quantity = min(remaining, order.remaining_quantity)
            required_cash += fill_quantity * order.price_ticks
            remaining -= fill_quantity

            if remaining == 0:
                break

        return required_cash

    def _required_cash(self, order: Order) -> Cash:
        if order.order_type is OrderType.MARKET:
            return self._get_market_buy_cost(order.symbol, order.original_quantity)

        if order.price_ticks is None:
            raise RuntimeError("Limit buy order must have a price")
        return order.original_quantity * order.price_ticks

    def _validate_order_request(self, request: RequestForOrder) -> None:
        """Ensure the given request is valid and the participant can fund it."""

        if request.participant_id not in self._participants:
            raise ValueError(f"Participant {request.participant_id} does not exist")

        if request.symbol not in self._instruments:
            raise ValueError(f"Symbol {request.symbol} does not exist")

        if request.order_type == OrderType.LIMIT and (
            request.price_ticks is None or request.price_ticks <= 0
        ):
            raise ValueError("Limit orders must have a positive price")

        if request.original_quantity <= 0:
            raise ValueError("Must have positive quantity")

        participant = self._participants[request.participant_id]
        if request.side is Side.BUY:
            if request.order_type == OrderType.LIMIT:
                assert request.price_ticks is not None
                required_cash = request.original_quantity * request.price_ticks
            else:
                required_cash = self._get_market_buy_cost(
                    request.symbol, request.original_quantity
                )

            if participant.balance < required_cash:
                raise ValueError("Participant does not have the required funds")
        else:
            available = participant.positions.get(request.symbol, 0)
            if available < request.original_quantity:
                raise ValueError(f"Participant does not hold enough {request.symbol}")

    def _reserve_order(self, order: Order) -> None:
        """Move available participant assets into exchange-owned order escrow."""
        participant = self._participants[order.participant_id]

        if order.side is Side.BUY:
            required_cash = self._required_cash(order)
            if participant.balance < required_cash:
                raise RuntimeError("Validated participant balance changed unexpectedly")

            participant.balance -= required_cash
            self._reserved_cash[order.order_id] = required_cash
            return

        available = participant.positions.get(order.symbol, 0)
        if available < order.original_quantity:
            raise RuntimeError("Validated participant position changed unexpectedly")

        participant.positions[order.symbol] = available - order.original_quantity
        self._reserved_positions[order.order_id] = order.original_quantity

    def _release_reservation(self, order: Order) -> None:
        """Return an order's remaining escrow to its participant."""
        participant = self._participants[order.participant_id]

        if order.side is Side.BUY:
            participant.balance += self._reserved_cash.pop(order.order_id, 0)
            return

        quantity = self._reserved_positions.pop(order.order_id, 0)
        participant.positions[order.symbol] = (
            participant.positions.get(order.symbol, 0) + quantity
        )

    def _orders_cross(self, incoming: Order, resting: Order) -> bool:
        """Determines whether two orders from opposite sides cross. Orders always
        cross when the incoming order is a market order."""

        if incoming.side is resting.side:
            raise ValueError("Orders must be from opposite sides")

        if incoming.order_type is OrderType.MARKET:
            return True

        # Logically, the two orders must have a price as they're now ruled out from
        # being market orders
        assert incoming.price_ticks is not None
        assert resting.price_ticks is not None

        if incoming.side is Side.BUY and incoming.price_ticks >= resting.price_ticks:
            return True

        return (
            incoming.side is Side.SELL and incoming.price_ticks <= resting.price_ticks
        )

    def _execute_trade(self, incoming: Order, resting: Order) -> Trade:
        """Executes a trade by matching two crossing orders."""
        quantity = min(
            incoming.remaining_quantity,
            resting.remaining_quantity,
        )

        if resting.price_ticks is None:
            raise RuntimeError("Resting order must have a price")

        if incoming.symbol != resting.symbol:
            raise RuntimeError(
                "Cannot create a trade on two orders for different instruments"
            )

        buy_order = incoming if incoming.side is Side.BUY else resting
        sell_order = incoming if incoming.side is Side.SELL else resting

        actual_cost = quantity * resting.price_ticks

        if buy_order.order_type is OrderType.LIMIT:
            if buy_order.price_ticks is None:
                raise RuntimeError("Limit buy order must have a price")
            reserved_for_fill = quantity * buy_order.price_ticks
        else:
            reserved_for_fill = actual_cost

        reserved_cash = self._reserved_cash.get(buy_order.order_id)
        if reserved_cash is None or reserved_cash < reserved_for_fill:
            raise RuntimeError("Buy order does not have enough reserved cash")

        reserved_positions = self._reserved_positions.get(sell_order.order_id)
        if reserved_positions is None or reserved_positions < quantity:
            raise RuntimeError("Sell order does not have enough reserved positions")

        incoming.apply_fill(quantity)
        resting.apply_fill(quantity)

        buyer = self._participants[buy_order.participant_id]
        seller = self._participants[sell_order.participant_id]

        remaining_cash = reserved_cash - reserved_for_fill
        if remaining_cash == 0:
            del self._reserved_cash[buy_order.order_id]
        else:
            self._reserved_cash[buy_order.order_id] = remaining_cash

        remaining_positions = reserved_positions - quantity
        if remaining_positions == 0:
            del self._reserved_positions[sell_order.order_id]
        else:
            self._reserved_positions[sell_order.order_id] = remaining_positions

        buyer.balance += reserved_for_fill - actual_cost
        buyer.positions[buy_order.symbol] = (
            buyer.positions.get(buy_order.symbol, 0) + quantity
        )
        seller.balance += actual_cost

        trade = Trade(
            trade_id=self._generate_trade_id(),
            symbol=incoming.symbol,
            price_ticks=resting.price_ticks,
            quantity=quantity,
            buy_order_id=buy_order.order_id,
            sell_order_id=sell_order.order_id,
            buyer_id=buy_order.participant_id,
            seller_id=sell_order.participant_id,
            sequence=self._generate_sequence_number(),
            timestamp=self._time(),
        )

        self._trades.append(trade)

        if resting.remaining_quantity == 0:
            book = self._order_books[resting.symbol]
            removed = book.pop_best(resting.side)

            # Logically, the resting order should have been the "best"
            assert removed is not None
            assert removed is resting

            self._active_orders.pop(resting.order_id)

        return trade

    def _process_order(self, incoming: Order) -> None:
        """Attempts to match an incoming order against resting orders in the relevant
        order book."""

        book = self._order_books[incoming.symbol]

        while incoming.remaining_quantity > 0:
            resting = book.best_ask if incoming.side is Side.BUY else book.best_bid

            if resting is None:
                break

            if not self._orders_cross(incoming, resting):
                break

            self._execute_trade(incoming, resting)

        if incoming.remaining_quantity == 0:
            self._active_orders.pop(incoming.order_id)
        elif incoming.order_type is OrderType.LIMIT:
            book.add_order(incoming)
        else:
            self.cancel_order(incoming.order_id)

    def require_order_ownership(
        self,
        participant_id: ParticipantId,
        order_id: OrderId,
    ) -> None:
        """Requires the given order to be owned by the given participant."""
        order = self._orders.get(order_id, None)
        if order is None:
            raise ValueError(f"{order_id} is not associated with any order")

        if self._participants.get(participant_id, None) is None:
            raise ValueError(f"{participant_id} is not associated with any participant")

        if order.participant_id != participant_id:
            raise ValueError(
                f"Participant {participant_id} does not own order {order_id}"
            )

    def get_book_snapshot(self, symbol: Symbol) -> BookSnapshot:
        """Return an immutable snapshot of an instrument's order book."""
        book = self._order_books.get(symbol)
        if book is None:
            raise ValueError(f"{symbol} has no associated order book")

        return book.snapshot()

    def get_trades(self) -> tuple[Trade, ...]:
        """Return an immutable snapshot of completed trades."""
        return tuple(self._trades)

    def cancel_order(self, order_id: OrderId) -> None:
        """Cancels an active order."""
        order = self._active_orders.get(order_id)
        if order is None:
            raise ValueError("Provided Order ID does not refer to any active order")

        if order.order_type is OrderType.LIMIT:
            book = self._order_books[order.symbol]
            removed = book.cancel_order(order.order_id, order.side)
            if removed is not order:
                raise RuntimeError("Active limit order was not found in its order book")
        else:
            order.cancel()

        self._release_reservation(order)
        del self._active_orders[order_id]

    def add_instrument(self, instrument: Instrument) -> None:
        """Adds an instrument to the exchange."""
        if instrument.symbol in self._instruments:
            raise ValueError(f"Instrument already exists: {instrument.symbol}")

        self._instruments[instrument.symbol] = instrument
        self._order_books[instrument.symbol] = OrderBook(instrument)

    def add_participant(self, participant: Participant) -> None:
        """Adds a participant to the exchange."""
        if participant.participant_id in self._participants:
            raise ValueError(
                f"Participant already exists: {participant.participant_id}"
            )

        self._participants[participant.participant_id] = participant

    def place_order(self, request: RequestForOrder) -> Order:
        """Request to place an order on the exchange.

        Parameters:
            request (OrderRequest): The order you are requesting to place.

        """
        self._validate_order_request(request)

        order = Order(
            order_id=self._generate_order_id(),
            participant_id=request.participant_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            original_quantity=request.original_quantity,
            remaining_quantity=request.original_quantity,
            price_ticks=request.price_ticks,
            sequence=self._generate_sequence_number(),
            timestamp=self._time(),
            status=OrderStatus.OPEN,
        )

        self._reserve_order(order)
        self._orders[order.order_id] = order
        self._active_orders[order.order_id] = order

        self._process_order(order)

        return order

    def get_time(self) -> Timestamp:
        return self._time()
