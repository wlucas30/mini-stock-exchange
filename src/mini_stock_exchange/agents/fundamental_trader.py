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
from mini_stock_exchange.simulation import FundamentalValueEstimator

ACTION_PROBABILITY = 0.2
MISPRICING_THRESHOLD = 0.02
QUANTITY_MEAN = 10.0
QUANTITY_STD_DEV = 3.0
MAX_ORDER_QUANTITY = 10
MAX_ORDER_AGE = 100
MAX_ORDERS = 1


@dataclass(kw_only=True)
class FundamentalTrader:
    """A trading agent which submits informed order flow."""

    participant_id: ParticipantId
    fundamental_value_estimator: FundamentalValueEstimator

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        active_orders = exchange.get_participant_active_orders(self.participant_id)
        for order in active_orders:
            if timestamp - order.timestamp >= MAX_ORDER_AGE:
                exchange.cancel_participant_order(
                    self.participant_id,
                    order.order_id,
                )

        if random.random() >= ACTION_PROBABILITY:
            return

        if exchange.count_participant_active_orders(self.participant_id) >= MAX_ORDERS:
            return

        symbols: tuple[Symbol, ...] = exchange.get_instrument_symbols()
        if not symbols:
            return

        symbol: Symbol = random.choice(symbols)

        value_estimate: PriceTicks = self.fundamental_value_estimator(symbol)

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

        book = exchange.get_book_snapshot(symbol)
        opportunities: list[tuple[Side, PriceTicks]] = []

        if book.asks:
            best_ask = book.asks[0].price_ticks
            buy_threshold = value_estimate * (1 - MISPRICING_THRESHOLD)

            if participant.available_cash >= best_ask and best_ask <= buy_threshold:
                opportunities.append((Side.BUY, best_ask))

        if book.bids:
            best_bid = book.bids[0].price_ticks
            sell_threshold = value_estimate * (1 + MISPRICING_THRESHOLD)

            if available_quantity > 0 and best_bid >= sell_threshold:
                opportunities.append((Side.SELL, best_bid))

        if not opportunities:
            return

        side, price_ticks = random.choice(opportunities)

        if side is Side.BUY:
            maximum_quantity = min(
                participant.available_cash // price_ticks,
                MAX_ORDER_QUANTITY,
            )
        else:
            maximum_quantity = min(
                available_quantity,
                MAX_ORDER_QUANTITY,
            )

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
        )

        exchange.place_order(request)
