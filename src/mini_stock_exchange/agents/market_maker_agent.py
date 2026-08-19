from dataclasses import dataclass, field

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    OrderType,
    ParticipantId,
    RequestForOrder,
    Side,
    Timestamp,
)
from mini_stock_exchange.simulation import FundamentalValueEstimator

HALF_SPREAD_FRACTION = 0.02
QUOTE_QUANTITY = 10
QUOTE_LIFETIME = 100
TARGET_INVENTORY_FRACTION = 0.05
MAX_INVENTORY_SKEW = 0.02


@dataclass(kw_only=True)
class MarketMakerAgent:
    """A trading agent intended to provide continuous two-sided liquidity."""

    participant_id: ParticipantId
    fundamental_value_estimator: FundamentalValueEstimator
    _next_quote_at: Timestamp | None = field(default=None, init=False, repr=False)

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        """Continously provide two-way quotes for each instrument."""
        if self._next_quote_at is not None and timestamp < self._next_quote_at:
            return

        symbols = exchange.get_instrument_symbols()
        if not symbols:
            return

        expires_at = timestamp + QUOTE_LIFETIME

        for instrument in exchange.get_instruments():
            symbol = instrument.symbol
            value_estimate = self.fundamental_value_estimator(symbol)

            participant = exchange.get_participant_details(self.participant_id)
            position = next(
                (
                    position
                    for position in participant.positions
                    if position.symbol == symbol
                ),
                None,
            )
            current_inventory = position.total_quantity if position is not None else 0
            target_inventory = max(
                1,
                round(instrument.total_supply * TARGET_INVENTORY_FRACTION),
            )
            inventory_error = (current_inventory - target_inventory) / target_inventory
            bounded_error = max(-1.0, min(1.0, inventory_error))
            price_skew = MAX_INVENTORY_SKEW * bounded_error

            adjusted_value = round(value_estimate * (1 - price_skew))

            bid_price = max(1, round(adjusted_value * (1 - HALF_SPREAD_FRACTION)))
            ask_price = max(
                bid_price + 1,
                round(adjusted_value * (1 + HALF_SPREAD_FRACTION)),
            )

            bid_quantity = min(
                QUOTE_QUANTITY,
                participant.available_cash // bid_price,
            )
            if bid_quantity > 0:
                exchange.place_order(
                    RequestForOrder(
                        participant_id=self.participant_id,
                        symbol=symbol,
                        side=Side.BUY,
                        order_type=OrderType.LIMIT,
                        original_quantity=bid_quantity,
                        price_ticks=bid_price,
                        expires_at=expires_at,
                    )
                )

            participant = exchange.get_participant_details(self.participant_id)
            position = next(
                (
                    position
                    for position in participant.positions
                    if position.symbol == symbol
                ),
                None,
            )
            ask_quantity = min(
                QUOTE_QUANTITY,
                position.available_quantity if position is not None else 0,
            )
            if ask_quantity > 0:
                exchange.place_order(
                    RequestForOrder(
                        participant_id=self.participant_id,
                        symbol=symbol,
                        side=Side.SELL,
                        order_type=OrderType.LIMIT,
                        original_quantity=ask_quantity,
                        price_ticks=ask_price,
                        expires_at=expires_at,
                    )
                )

        self._next_quote_at = expires_at
