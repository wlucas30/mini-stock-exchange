from dataclasses import dataclass

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    Order,
    OrderId,
    Participant,
    ParticipantSummary,
    PriceTicks,
    RequestForOrder,
    Symbol,
    Timestamp,
    Trade,
)
from mini_stock_exchange.exchange.order_book import BookSnapshot

from .command import (
    AddInstrument,
    AddParticipant,
    CancelOrder,
    Command,
    ListInstruments,
    ListParticipants,
    PlaceOrder,
    ShowBook,
    ShowGraph,
    ShowTime,
    ShowTrades,
)

type ExecutorResponse = (
    ErrorResponse
    | AddInstrumentResponse
    | AddParticipantResponse
    | ListInstrumentsResponse
    | ListParticipantsResponse
    | PlaceOrderResponse
    | CancelOrderResponse
    | ShowBookResponse
    | ShowTradesResponse
    | ShowTimeResponse
    | ShowGraphResponse
)


@dataclass(frozen=True, kw_only=True)
class ErrorResponse:
    """The response returned by the command executor when an error occurs."""

    message: str


@dataclass(frozen=True, kw_only=True)
class AddInstrumentResponse:
    instrument: Instrument


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


@dataclass(frozen=True, kw_only=True)
class GraphEntry:
    timestamp: Timestamp
    price_ticks: PriceTicks


class Executor:
    def __init__(self, exchange: Exchange) -> None:
        self._exchange = exchange

    def execute(self, command: Command) -> ExecutorResponse:
        match command:
            case AddInstrument(symbol=symbol):
                instrument = Instrument(symbol=symbol)

                try:
                    self._exchange.add_instrument(instrument)
                    return AddInstrumentResponse(instrument=instrument)
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

                return ShowGraphResponse(symbol=symbol, entries=entries)
