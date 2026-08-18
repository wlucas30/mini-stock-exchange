from dataclasses import dataclass

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    Order,
    OrderId,
    Participant,
    ParticipantDetails,
    ParticipantSummary,
    PriceTicks,
    Quantity,
    RequestForOrder,
    Symbol,
    Timestamp,
    Trade,
)
from mini_stock_exchange.exchange.order_book import BookSnapshot
from mini_stock_exchange.simulation import Simulation

from .command import (
    AddInstrument,
    AddParticipant,
    CancelOrder,
    Command,
    FastForward,
    ListInstruments,
    ListParticipants,
    PlaceOrder,
    SetTimeMultiplier,
    ShowBook,
    ShowGraph,
    ShowParticipant,
    ShowTime,
    ShowTrades,
)

type ExecutorResponse = (
    ErrorResponse
    | AddInstrumentResponse
    | AddParticipantResponse
    | ListInstrumentsResponse
    | ListParticipantsResponse
    | FastForwardResponse
    | PlaceOrderResponse
    | CancelOrderResponse
    | ShowBookResponse
    | ShowTradesResponse
    | ShowTimeResponse
    | ShowGraphResponse
    | ShowParticipantResponse
    | SetTimeMultiplierResponse
)


@dataclass(frozen=True, kw_only=True)
class ErrorResponse:
    """The response returned by the command executor when an error occurs."""

    message: str


@dataclass(frozen=True, kw_only=True)
class AddInstrumentResponse:
    instrument: Instrument
    price_ticks: PriceTicks
    volume: Quantity


@dataclass(frozen=True, kw_only=True)
class AddParticipantResponse:
    participant: Participant


@dataclass(frozen=True, kw_only=True)
class ListInstrumentsResponse:
    symbols: tuple[Symbol, ...]


@dataclass(frozen=True, kw_only=True)
class ListParticipantsResponse:
    participants: tuple[ParticipantSummary, ...]


@dataclass(frozen=True, kw_only=True)
class FastForwardResponse:
    timestamp: Timestamp


@dataclass(frozen=True, kw_only=True)
class SetTimeMultiplierResponse:
    multiplier: int


@dataclass(frozen=True, kw_only=True)
class PlaceOrderResponse:
    order: Order


@dataclass(frozen=True, kw_only=True)
class CancelOrderResponse:
    order_id: OrderId


@dataclass(frozen=True, kw_only=True)
class ShowTimeResponse:
    timestamp: Timestamp


@dataclass(frozen=True, kw_only=True)
class ShowBookResponse:
    book: BookSnapshot


@dataclass(frozen=True, kw_only=True)
class ShowTradesResponse:
    trades: tuple[Trade, ...]


@dataclass(frozen=True, kw_only=True)
class ShowGraphResponse:
    symbol: Symbol
    entries: tuple[GraphEntry, ...]
    fundamental_entries: tuple[GraphEntry, ...] = ()


@dataclass(frozen=True, kw_only=True)
class ShowParticipantResponse:
    participant: ParticipantDetails


@dataclass(frozen=True, kw_only=True)
class GraphEntry:
    timestamp: Timestamp
    price_ticks: PriceTicks


class Executor:
    def __init__(
        self,
        exchange: Exchange,
        simulation: Simulation | None = None,
    ) -> None:
        self._exchange = exchange
        self._simulation = simulation

    def execute(self, command: Command) -> ExecutorResponse:
        match command:
            case AddInstrument(
                symbol=symbol,
                price_ticks=price_ticks,
                volume=volume,
            ):
                instrument = Instrument(symbol=symbol)

                try:
                    if self._simulation is None:
                        return ErrorResponse(message="Simulation is unavailable")

                    self._simulation.issue_instrument(
                        instrument=instrument,
                        price_ticks=price_ticks,
                        volume=volume,
                    )
                    return AddInstrumentResponse(
                        instrument=instrument,
                        price_ticks=price_ticks,
                        volume=volume,
                    )
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to add instrument: {error}")

            case AddParticipant(participant_id=participant_id):
                participant = Participant(
                    participant_id=participant_id,
                    display_name=participant_id,
                )

                try:
                    self._exchange.add_participant(participant)
                    return AddParticipantResponse(participant=participant)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to add participant: {error}")

            case ListInstruments():
                return ListInstrumentsResponse(
                    symbols=self._exchange.get_instrument_symbols()
                )

            case ListParticipants():
                return ListParticipantsResponse(
                    participants=self._exchange.get_participant_summaries()
                )

            case SetTimeMultiplier(multiplier=multiplier):
                if self._simulation is None:
                    return ErrorResponse(message="Simulation is unavailable")

                self._simulation.multiplier = multiplier
                return SetTimeMultiplierResponse(multiplier=multiplier)

            case FastForward(delta=delta):
                if self._simulation is None:
                    return ErrorResponse(message="Simulation is unavailable")

                timestamp = self._simulation.fast_forward(delta)
                return FastForwardResponse(timestamp=timestamp)

            case PlaceOrder():
                request = RequestForOrder(
                    participant_id=command.participant_id,
                    symbol=command.symbol,
                    side=command.side,
                    order_type=command.order_type,
                    original_quantity=command.quantity,
                    price_ticks=command.price_ticks,
                )

                try:
                    order = self._exchange.place_order(request)
                    return PlaceOrderResponse(order=order)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to place order: {error}")

            case CancelOrder(participant_id=participant_id, order_id=order_id):
                try:
                    self._exchange.require_order_ownership(participant_id, order_id)
                    self._exchange.cancel_order(order_id)
                    return CancelOrderResponse(order_id=order_id)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to cancel order: {error}")

            case ShowBook(symbol=symbol):
                try:
                    book = self._exchange.get_book_snapshot(symbol)
                    return ShowBookResponse(book=book)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to get order book: {error}")

            case ShowParticipant(participant_id=participant_id):
                try:
                    participant = self._exchange.get_participant_details(participant_id)
                    return ShowParticipantResponse(participant=participant)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to get participant: {error}")

            case ShowTrades():
                try:
                    return ShowTradesResponse(trades=self._exchange.get_trades())
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to get trades: {error}")

            case ShowTime():
                try:
                    return ShowTimeResponse(timestamp=self._exchange.get_time())
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to get time: {error}")

            case ShowGraph(symbol=symbol):
                try:
                    trades = self._exchange.get_trades_by_symbol(symbol)
                except ValueError as error:
                    return ErrorResponse(message=f"Failed to generate graph: {error}")

                entries = tuple(
                    GraphEntry(
                        timestamp=trade.timestamp,
                        price_ticks=trade.price_ticks,
                    )
                    for trade in trades
                )

                fundamental_entries = (
                    tuple(
                        GraphEntry(
                            timestamp=entry.timestamp,
                            price_ticks=entry.price_ticks,
                        )
                        for entry in self._simulation.get_fundamental_value_history(
                            symbol
                        )
                    )
                    if self._simulation is not None
                    else ()
                )

                return ShowGraphResponse(
                    symbol=symbol,
                    entries=entries,
                    fundamental_entries=fundamental_entries,
                )
