"""Defines our internal Command datatype which the parser converts tokens into."""

from dataclasses import dataclass

from mini_stock_exchange.exchange.models import (
    OrderType,
    ParticipantId,
    PriceTicks,
    Quantity,
    Side,
    Symbol,
    Timestamp,
)

type Command = (
    AddInstrument
    | AddParticipant
    | ListInstruments
    | ListParticipants
    | FastForward
    | PlaceOrder
    | CancelOrder
    | ShowBook
    | ShowTrades
    | ShowTime
    | ShowGraph
    | ShowStats
    | ShowParticipant
    | ShowPerformance
    | SetTimeMultiplier
)


@dataclass(frozen=True, kw_only=True)
class AddInstrument:
    symbol: Symbol
    price_ticks: PriceTicks
    volume: Quantity


@dataclass(frozen=True, kw_only=True)
class AddParticipant:
    participant_id: ParticipantId


@dataclass(frozen=True, kw_only=True)
class ListInstruments:
    pass


@dataclass(frozen=True, kw_only=True)
class ListParticipants:
    pass


@dataclass(frozen=True, kw_only=True)
class FastForward:
    delta: Timestamp


@dataclass(frozen=True, kw_only=True)
class SetTimeMultiplier:
    multiplier: int


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
class ShowParticipant:
    participant_id: ParticipantId


@dataclass(frozen=True, kw_only=True)
class ShowPerformance:
    participant_id: ParticipantId


@dataclass(frozen=True, kw_only=True)
class ShowTrades:
    pass


@dataclass(frozen=True, kw_only=True)
class ShowTime:
    pass


@dataclass(frozen=True, kw_only=True)
class ShowGraph:
    symbol: Symbol


@dataclass(frozen=True, kw_only=True)
class ShowStats:
    symbol: Symbol
