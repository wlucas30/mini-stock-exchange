"""Defines our internal Command datatype which the parser converts tokens into."""

from dataclasses import dataclass

from mini_stock_exchange.exchange.models import (
    OrderType,
    ParticipantId,
    PriceTicks,
    Quantity,
    Side,
    Symbol,
)


type Command = (
    AddInstrument
    | AddParticipant
    | PlaceOrder
    | CancelOrder
    | ShowBook
    | ShowTrades
    | ShowTime
    | ShowGraph
)


@dataclass(frozen=True, kw_only=True)
class AddInstrument:
    symbol: Symbol


@dataclass(frozen=True, kw_only=True)
class AddParticipant:
    participant_id: ParticipantId


@dataclass(frozen=True, kw_only=True)
class PlaceOrder:
    participant_id: ParticipantId
    side: Side
    symbol: Symbol
    order_type: OrderType
    quantity: Quantity
    price_ticks: PriceTicks | None


@dataclass(frozen=True, kw_only=True)
class CancelOrder:
    participant_id: ParticipantId
    order_id: int


@dataclass(frozen=True, kw_only=True)
class ShowBook:
    symbol: Symbol


@dataclass(frozen=True, kw_only=True)
class ShowTrades:
    pass


@dataclass(frozen=True, kw_only=True)
class ShowTime:
    pass


@dataclass(frozen=True, kw_only=True)
class ShowGraph:
    symbol: Symbol
    