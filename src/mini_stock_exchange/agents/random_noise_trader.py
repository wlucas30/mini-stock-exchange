import random
from dataclasses import dataclass

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    OrderType,
    ParticipantDetails,
    ParticipantId,
    ParticipantPositionSummary,
    PriceTicks,
    Quantity,
    RequestForOrder,
    Side,
    Symbol,
    Timestamp,
)

ACTION_PROBABILITY = 0.2
PRICE_STD_DEV_FRACTION = 0.0025
QUANTITY_MEAN = 10.0
QUANTITY_STD_DEV = 3.0
MAX_ORDER_QUANTITY = 20
ORDER_LIFETIME = 25
MAX_ORDERS = 1


@dataclass(kw_only=True)
class RandomNoiseTrader:
    """A trading agent which submits uninformed, random order flow."""

    participant_id: ParticipantId

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        if random.random() >= ACTION_PROBABILITY:
            return

        if exchange.count_participant_active_orders(self.participant_id) >= MAX_ORDERS:
            return

        symbols: tuple[Symbol, ...] = exchange.get_instrument_symbols()
        if not symbols:
            return

        symbol: Symbol = random.choice(symbols)
        participant: ParticipantDetails = exchange.get_participant_details(
            self.participant_id
        )

        position: ParticipantPositionSummary | None = next(
            (
                position
                for position in participant.positions
                if position.symbol == symbol
            ),
            None,
        )

        available_quantity: Quantity = (
            position.available_quantity if position is not None else 0
        )

        feasible_sides: list[Side] = []

        if participant.available_cash > 0:
            feasible_sides.append(Side.BUY)

        if available_quantity > 0:
            feasible_sides.append(Side.SELL)

        if not feasible_sides:
            return

        side: Side = random.choice(feasible_sides)

        ref_price_ticks = exchange.get_reference_price(symbol)
        if ref_price_ticks is None:
            return

        if side is Side.BUY:
            maximum_quantity = participant.available_cash // ref_price_ticks
        else:
            maximum_quantity = available_quantity

        if maximum_quantity == 0:
            return

        price_std_dev = max(1.0, ref_price_ticks * PRICE_STD_DEV_FRACTION)
        price_ticks: PriceTicks = max(
            1,
            round(random.gauss(ref_price_ticks, price_std_dev)),
        )

        if side is Side.BUY:
            affordable_quantity = participant.available_cash // price_ticks
            maximum_quantity = min(affordable_quantity, MAX_ORDER_QUANTITY)
        else:
            maximum_quantity = min(available_quantity, MAX_ORDER_QUANTITY)

        if maximum_quantity < 1:
            return

        quantity = round(random.gauss(QUANTITY_MEAN, QUANTITY_STD_DEV))
        quantity = max(1, min(quantity, maximum_quantity))

        request = RequestForOrder(
            participant_id=self.participant_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            original_quantity=quantity,
            price_ticks=price_ticks,
            expires_at=timestamp + ORDER_LIFETIME,
        )

        exchange.place_order(request)
