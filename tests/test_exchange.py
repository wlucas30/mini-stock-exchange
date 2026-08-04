from decimal import Decimal

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    OrderStatus,
    OrderType,
    Participant,
    RequestForOrder,
    Side,
)


# Helper for creating a dummy exchange
def make_exchange(*participants: Participant) -> Exchange:
    exchange = Exchange(time=lambda: 123)
    exchange.add_instrument(Instrument(symbol="AAPL", tick_size=Decimal("0.01")))
    for participant in participants:
        exchange.add_participant(participant)
    return exchange


# Helper for creating a dummy request
def make_request(
    participant_id: str,
    side: Side,
    quantity: int,
    price: int | None,
    order_type: OrderType = OrderType.LIMIT,
) -> RequestForOrder:
    return RequestForOrder(
        participant_id=participant_id,
        symbol="AAPL",
        side=side,
        order_type=order_type,
        original_quantity=quantity,
        price_bps=price,
    )


def test_exchange_uses_injected_time_provider() -> None:
    exchange = Exchange(time=lambda: 123)

    assert exchange._time() == 123


def test_cancel_buy_limit_returns_reserved_cash() -> None:
    buyer = Participant("buyer", "Buyer", balance=1_000)
    exchange = make_exchange(buyer)
    order = exchange.place_order(
        make_request("buyer", side=Side.BUY, quantity=5, price=100)
    )

    assert buyer.balance == 500
    assert exchange._reserved_cash == {order.order_id: 500}

    exchange.cancel_order(order.order_id)

    assert order.status is OrderStatus.CANCELLED
    assert buyer.balance == 1_000
    assert exchange._reserved_cash == {}
    assert exchange._order_books["AAPL"].best_bid is None


def test_cancel_sell_limit_returns_reserved_positions() -> None:
    seller = Participant("seller", "Seller", positions={"AAPL": 10})
    exchange = make_exchange(seller)
    order = exchange.place_order(
        make_request("seller", side=Side.SELL, quantity=6, price=100)
    )

    assert seller.positions["AAPL"] == 4
    assert exchange._reserved_positions == {order.order_id: 6}

    exchange.cancel_order(order.order_id)

    assert order.status is OrderStatus.CANCELLED
    assert seller.positions["AAPL"] == 10
    assert exchange._reserved_positions == {}
    assert exchange._order_books["AAPL"].best_ask is None


def test_full_fill_settles_escrow_and_refunds_price_improvement() -> None:
    buyer = Participant("buyer", "Buyer", balance=1_000)
    seller = Participant("seller", "Seller", balance=0, positions={"AAPL": 5})
    exchange = make_exchange(buyer, seller)
    sell_order = exchange.place_order(
        make_request("seller", side=Side.SELL, quantity=5, price=90)
    )
    buy_order = exchange.place_order(
        make_request("buyer", side=Side.BUY, quantity=5, price=100)
    )

    assert sell_order.status is OrderStatus.FILLED
    assert buy_order.status is OrderStatus.FILLED
    assert buyer.balance == 550
    assert buyer.positions["AAPL"] == 5
    assert seller.balance == 450
    assert seller.positions["AAPL"] == 0
    assert exchange._reserved_cash == {}
    assert exchange._reserved_positions == {}


def test_cancel_partially_filled_buy_returns_only_remaining_escrow() -> None:
    buyer = Participant("buyer", "Buyer", balance=1_000)
    seller = Participant("seller", "Seller", balance=0, positions={"AAPL": 2})
    exchange = make_exchange(buyer, seller)
    exchange.place_order(make_request("seller", side=Side.SELL, quantity=2, price=90))
    buy_order = exchange.place_order(
        make_request("buyer", side=Side.BUY, quantity=5, price=100)
    )

    assert buy_order.status is OrderStatus.PARTIALLY_FILLED
    assert buyer.balance == 520
    assert buyer.positions["AAPL"] == 2
    assert exchange._reserved_cash == {buy_order.order_id: 300}

    exchange.cancel_order(buy_order.order_id)

    assert buyer.balance == 820
    assert buy_order.status is OrderStatus.CANCELLED
    assert exchange._reserved_cash == {}


def test_cancel_partially_filled_sell_returns_only_remaining_positions() -> None:
    buyer = Participant("buyer", "Buyer", balance=1_000)
    seller = Participant("seller", "Seller", balance=0, positions={"AAPL": 5})
    exchange = make_exchange(buyer, seller)
    exchange.place_order(make_request("buyer", side=Side.BUY, quantity=2, price=100))
    sell_order = exchange.place_order(
        make_request("seller", side=Side.SELL, quantity=5, price=90)
    )

    assert sell_order.status is OrderStatus.PARTIALLY_FILLED
    assert seller.balance == 200
    assert seller.positions["AAPL"] == 0
    assert exchange._reserved_positions == {sell_order.order_id: 3}

    exchange.cancel_order(sell_order.order_id)

    assert seller.positions["AAPL"] == 3
    assert sell_order.status is OrderStatus.CANCELLED
    assert exchange._reserved_positions == {}


def test_unfilled_market_sell_returns_positions() -> None:
    seller = Participant("seller", "Seller", positions={"AAPL": 5})
    exchange = make_exchange(seller)

    order = exchange.place_order(
        make_request(
            "seller",
            side=Side.SELL,
            quantity=5,
            price=None,
            order_type=OrderType.MARKET,
        )
    )

    assert order.status is OrderStatus.CANCELLED
    assert seller.positions["AAPL"] == 5
    assert exchange._reserved_positions == {}


def test_market_buy_cost_does_not_remove_resting_asks() -> None:
    buyer = Participant("buyer", "Buyer", balance=1_000)
    seller = Participant("seller", "Seller", balance=0, positions={"AAPL": 2})
    exchange = make_exchange(buyer, seller)
    exchange.place_order(make_request("seller", side=Side.SELL, quantity=2, price=90))

    buy_order = exchange.place_order(
        make_request(
            "buyer",
            side=Side.BUY,
            quantity=2,
            price=None,
            order_type=OrderType.MARKET,
        )
    )

    assert buy_order.status is OrderStatus.FILLED
    assert buyer.balance == 820
    assert buyer.positions["AAPL"] == 2
    assert seller.balance == 180
    assert exchange._reserved_cash == {}
