import pytest

from mini_stock_exchange.commands.command import (
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
    ShowStats,
    ShowTime,
    ShowTrades,
)
from mini_stock_exchange.commands.lexer import lex
from mini_stock_exchange.commands.parser import Parser, ParserError
from mini_stock_exchange.exchange.models import OrderType, Side


def parse(source: str) -> Command:
    return Parser(lex(source)).parse()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "ADD INSTR AAPL PRICE 10000 VOLUME 100",
            AddInstrument(symbol="AAPL", price_ticks=10000, volume=100),
        ),
        ("ADD PARTICIPANT ALICE", AddParticipant(participant_id="ALICE")),
        ("LIST INSTR", ListInstruments()),
        ("LIST PARTICIPANT", ListParticipants()),
        ("SET TIME MULTIPLIER 0", SetTimeMultiplier(multiplier=0)),
        ("SET TIME MULTIPLIER 5", SetTimeMultiplier(multiplier=5)),
        ("FAST FORWARD 30", FastForward(delta=30)),
        (
            "AS ALICE BUY AAPL MARKET QUANTITY 5",
            PlaceOrder(
                participant_id="ALICE",
                side=Side.BUY,
                symbol="AAPL",
                order_type=OrderType.MARKET,
                quantity=5,
                price_ticks=None,
            ),
        ),
        (
            "AS ALICE SELL AAPL MARKET QUANTITY 5",
            PlaceOrder(
                participant_id="ALICE",
                side=Side.SELL,
                symbol="AAPL",
                order_type=OrderType.MARKET,
                quantity=5,
                price_ticks=None,
            ),
        ),
        (
            "AS ALICE BUY AAPL LIMIT PRICE 100 QUANTITY 5",
            PlaceOrder(
                participant_id="ALICE",
                side=Side.BUY,
                symbol="AAPL",
                order_type=OrderType.LIMIT,
                quantity=5,
                price_ticks=100,
            ),
        ),
        (
            "AS ALICE SELL AAPL LIMIT PRICE 100 QUANTITY 5",
            PlaceOrder(
                participant_id="ALICE",
                side=Side.SELL,
                symbol="AAPL",
                order_type=OrderType.LIMIT,
                quantity=5,
                price_ticks=100,
            ),
        ),
        (
            "AS ALICE CANCEL ORDER 42",
            CancelOrder(participant_id="ALICE", order_id=42),
        ),
        ("SHOW BOOK AAPL", ShowBook(symbol="AAPL")),
        (
            "SHOW PARTICIPANT ALICE",
            ShowParticipant(participant_id="ALICE"),
        ),
        ("SHOW TRADES", ShowTrades()),
        ("SHOW TIME", ShowTime()),
        ("SHOW GRAPH AAPL", ShowGraph(symbol="AAPL")),
        ("SHOW STATS AAPL", ShowStats(symbol="AAPL")),
    ],
)
def test_parses_commands(source: str, expected: Command) -> None:
    assert parse(source) == expected


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "AS ALICE BUY AAPL LIMIT PRICE 100 QUANTITY 0",
            "Quantity must be positive",
        ),
        (
            "AS ALICE BUY AAPL LIMIT PRICE 0 QUANTITY 5",
            "Price must be positive",
        ),
        ("AS ALICE CANCEL ORDER 0", "Order ID must be positive"),
        (
            "ADD INSTR AAPL PRICE 0 VOLUME 100",
            "Price must be positive",
        ),
        (
            "ADD INSTR AAPL PRICE 10000 VOLUME 0",
            "Volume must be positive",
        ),
    ],
)
def test_rejects_nonpositive_integers(source: str, message: str) -> None:
    with pytest.raises(ParserError, match=message):
        parse(source)


@pytest.mark.parametrize(
    "source",
    [
        "",
        "ADD AAPL",
        "ADD INSTR AAPL",
        "ADD INSTR AAPL PRICE 10000",
        "AS ALICE BUY AAPL",
        "AS ALICE BUY AAPL LIMIT 100 QUANTITY 5",
        "AS ALICE BUY AAPL MARKET 5",
        "SHOW BOOK",
        "SHOW PARTICIPANT",
        "SHOW UNKNOWN",
        "LIST UNKNOWN",
        "SET TIME 2",
        "FAST 10",
    ],
)
def test_rejects_incomplete_or_unknown_commands(source: str) -> None:
    with pytest.raises(ParserError):
        parse(source)


@pytest.mark.parametrize(
    "source",
    [
        "ADD INSTR AAPL PRICE 10000 VOLUME 100 EXTRA",
        "AS ALICE CANCEL ORDER 42 EXTRA",
        "AS ALICE BUY AAPL MARKET QUANTITY 5 EXTRA",
        "SHOW TIME EXTRA",
        "LIST INSTR EXTRA",
        "SET TIME MULTIPLIER 2 EXTRA",
        "FAST FORWARD 10 EXTRA",
    ],
)
def test_rejects_trailing_tokens(source: str) -> None:
    with pytest.raises(ParserError, match="Expected END"):
        parse(source)
