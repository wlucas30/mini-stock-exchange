from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto

type OrderId = int
type TradeId = int
type ParticipantId = str
type Symbol = str
type Price = int
type Cash = int  # 1 = $0.01
type Quantity = int
type Timestamp = int
type Sequence = int


class Side(Enum):
    """This decides which side an order is on. The only two options
    are BUY and SELL."""

    BUY = auto()
    SELL = auto()


class OrderType(Enum):
    """This decides whether an order is placed as a market or limit order."""

    LIMIT = auto()
    MARKET = auto()


class OrderStatus(Enum):
    """Represents the current status of an order."""

    OPEN = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()


@dataclass(frozen=True)
class Instrument:
    """Represents a single instrument traded on the exchange.

    Attributes:
        symbol (str): A globally unique string identifier such as AAPL.
        tick_size (Decimal): Represents the decimal size of one basis point.

    """

    symbol: Symbol
    tick_size: Decimal


@dataclass
class Order:
    """A single order accepted by the exchange.

    Remaining quantity and status may change as trades occur.

    Attributes:
        order_id (OrderId): A globally unique integer identifier.
        sequence (Sequence): The order's sequence number.
        participant_id (ParticipantId): The identifier of the participant that
            placed the order.
        symbol (Symbol): The string identifier of the instrument being ordered.
        side (Side): The side of the order.
        order_type (OrderType): Specifies whether this is a limit or market order.
        original_quantity (int): The quantity this order was placed at.
        remaining_quantity (int): Unfilled quantity remaining.
        timestamp (int): The timestamp the order was accepted at.
        price_bps (Price): For limit orders, the price the order was placed at in bps.
        status (OrderStatus): The current status of the order.

    """

    order_id: OrderId
    sequence: Sequence
    participant_id: ParticipantId
    symbol: Symbol
    side: Side
    order_type: OrderType
    original_quantity: Quantity
    remaining_quantity: Quantity
    timestamp: Timestamp
    price_bps: Price | None
    status: OrderStatus

    @property
    def filled_quantity(self) -> int:
        """The quantity of the order that has been filled."""
        return self.original_quantity - self.remaining_quantity

    @property
    def is_active(self) -> bool:
        """Returns whether the order is currently active."""
        return self.status in {
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED,
        }

    def apply_fill(self, quantity: int) -> None:
        """Reduces the remaining quantity by the given value.

        Parameters:
            quantity (int): The positive quantity to be filled.

        """
        if quantity <= 0:
            raise ValueError("Fill quantity must be positive")

        if quantity > self.remaining_quantity:
            raise ValueError("Cannot fill more than the remaining quantity")

        if not self.is_active:
            raise ValueError("Cannot fill an inactive order")

        self.remaining_quantity -= quantity

        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        """Cancels an active order."""
        if not self.is_active:
            raise ValueError("Only active orders can be cancelled")

        self.status = OrderStatus.CANCELLED


@dataclass(frozen=True)
class RequestForOrder:
    """A request to the exchange to place an order.

    The exchange assigns order ID and timestamp.

    Attributes:
        participant_id (ParticipantId): The identifier of the participant placing
            the order.
        symbol (Symbol): The string identifier of the instrument being ordered.
        side (Side): The side of the order.
        order_type (OrderType): Specifies whether this is a limit or market order.
        original_quantity (int): The quantity this order is to be placed at.
        price_bps (Price): For limit orders, the price the order is to be placed at
            in bps.

    """

    participant_id: ParticipantId
    symbol: Symbol
    side: Side
    order_type: OrderType
    original_quantity: Quantity
    price_bps: Price | None


@dataclass(frozen=True)
class Trade:
    """Represents a match between a buy and sell order where instruments are exchanged
    between participants.

    Attributes:
        trade_id (TradeId): Globally unique identifier for this trade.
        sequence (Sequence): The trade's sequence number.
        symbol (Symbol): The symbol of the instrument being traded.
        price_bps (Price): The price in basis points at which the trade occurred.
        quantity (Quantity): Quantity traded.
        buy_order_id (OrderId): The identifier of the correpsonding buy order.
        sell_order_id (OrderId): The identifier of the corresponding sell order.
        buyer_id (ParticipantId): The identifier of the corresponding buyer.
        seller_id (ParticipantId): The identifier of the corresponding seller.
        timestamp (Timestamp): The timestamp at which the trade occurred.

    """

    trade_id: TradeId
    sequence: Sequence
    symbol: Symbol
    price_bps: Price
    quantity: Quantity

    buy_order_id: OrderId
    sell_order_id: OrderId

    buyer_id: ParticipantId
    seller_id: ParticipantId

    timestamp: Timestamp


@dataclass
class Participant:
    participant_id: ParticipantId
    display_name: str

    balance: Cash = field(
        default=10_000_00,  # $10,000
        repr=False,
    )
    positions: dict[Symbol, Quantity] = field(
        default_factory=dict[Symbol, Quantity],
        repr=False,
    )
