from .models import (
    Instrument,
    Order,
    OrderId,
    Participant,
    ParticipantId,
    Sequence,
    Symbol,
    Trade,
    TradeId,
)
from .order_book import OrderBook


class Exchange:
    def __init__(self) -> None:
        self._instruments: dict[Symbol, Instrument] = {}
        self._order_books: dict[Symbol, OrderBook] = {}
        self._participants: dict[ParticipantId, Participant] = {}

        self._active_orders: dict[OrderId, Order] = {}
        self._trades: list[Trade] = []

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

    def _generate_sequence_number(self) -> OrderId:
        sequence_number = self._next_sequence_number
        self._next_sequence_number += 1
        return sequence_number

    def add_instrument(self, instrument: Instrument) -> None:
        if instrument.symbol in self._instruments:
            raise ValueError(f"Instrument already exists: {instrument.symbol}")

        self._instruments[instrument.symbol] = instrument
        self._order_books[instrument.symbol] = OrderBook(instrument)

    def add_participant(self, participant: Participant) -> None:
        if participant.participant_id in self._participants:
            raise ValueError(
                f"Participant already exists: {participant.participant_id}"
            )

        self._participants[participant.participant_id] = participant
