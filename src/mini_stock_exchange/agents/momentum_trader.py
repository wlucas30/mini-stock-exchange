import random
from collections import deque
from dataclasses import dataclass, field

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    OrderType,
    ParticipantId,
    PriceTicks,
    RequestForOrder,
    Side,
    Symbol,
    Timestamp,
)

SHORT_WINDOW = 20
LONG_WINDOW = 100
SIGNAL_THRESHOLD = 0.005
ACTION_PROBABILITY = 0.05
MAX_ORDER_QUANTITY = 10
ORDER_LIFETIME = 10
MAX_ORDERS = 1


class _RollingAverage:
    def __init__(self, window_size: int) -> None:
        self._window_size = window_size
        self._prices: deque[PriceTicks] = deque()
        self._total = 0

    def observe(self, price_ticks: PriceTicks) -> None:
        if len(self._prices) == self._window_size:
            self._total -= self._prices.popleft()

        self._prices.append(price_ticks)
        self._total += price_ticks

    @property
    def value(self) -> float | None:
        if len(self._prices) < self._window_size:
            return None
        return self._total / self._window_size


class _MomentumState:
    def __init__(self) -> None:
        self._short_average = _RollingAverage(SHORT_WINDOW)
        self._long_average = _RollingAverage(LONG_WINDOW)

    def observe(self, price_ticks: PriceTicks) -> None:
        self._short_average.observe(price_ticks)
        self._long_average.observe(price_ticks)

    @property
    def signal(self) -> float | None:
        short_average = self._short_average.value
        long_average = self._long_average.value
        if short_average is None or long_average is None:
            return None
        return (short_average - long_average) / long_average


def _empty_momentum_states() -> dict[Symbol, _MomentumState]:
    return {}


@dataclass(kw_only=True)
class MomentumTrader:
    """Trades by observing current momentum for each instrument."""

    participant_id: ParticipantId
    _states: dict[Symbol, _MomentumState] = field(
        default_factory=_empty_momentum_states,
        init=False,
        repr=False,
    )

    def _get_state(self, symbol: Symbol) -> _MomentumState:
        state = self._states.get(symbol)
        if state is None:
            state = _MomentumState()
            self._states[symbol] = state
        return state

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        symbols = exchange.get_instrument_symbols()
        for symbol in symbols:
            price_ticks = exchange.get_reference_price(symbol)
            if price_ticks is not None:
                self._get_state(symbol).observe(price_ticks)

        if random.random() >= ACTION_PROBABILITY:
            return

        if exchange.count_participant_active_orders(self.participant_id) >= MAX_ORDERS:
            return

        participant = exchange.get_participant_details(self.participant_id)
        positions = {position.symbol: position for position in participant.positions}
        opportunities: list[tuple[Side, Symbol, PriceTicks]] = []

        for symbol in symbols:
            signal = self._get_state(symbol).signal
            if signal is None:
                continue

            book = exchange.get_book_snapshot(symbol)
            if signal >= SIGNAL_THRESHOLD and book.asks:
                best_ask = book.asks[0].price_ticks
                if participant.available_cash >= best_ask:
                    opportunities.append((Side.BUY, symbol, best_ask))
            elif signal <= -SIGNAL_THRESHOLD and book.bids:
                position = positions.get(symbol)
                if position is not None and position.available_quantity > 0:
                    opportunities.append((Side.SELL, symbol, book.bids[0].price_ticks))

        if not opportunities:
            return

        side, symbol, price_ticks = random.choice(opportunities)
        if side is Side.BUY:
            maximum_quantity = participant.available_cash // price_ticks
        else:
            maximum_quantity = positions[symbol].available_quantity

        quantity = min(MAX_ORDER_QUANTITY, maximum_quantity)
        if quantity < 1:
            return

        exchange.place_order(
            RequestForOrder(
                participant_id=self.participant_id,
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                original_quantity=quantity,
                price_ticks=price_ticks,
                expires_at=timestamp + ORDER_LIFETIME,
            )
        )
