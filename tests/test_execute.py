from mini_stock_exchange.commands.command import (
    AddInstrument,
    ListInstruments,
    ListParticipants,
    ShowGraph,
    ShowParticipant,
    ShowTime,
)
from mini_stock_exchange.commands.execute import (
    AddInstrumentResponse,
    ErrorResponse,
    Executor,
    GraphEntry,
    ListInstrumentsResponse,
    ListParticipantsResponse,
    ShowGraphResponse,
    ShowParticipantResponse,
    ShowTimeResponse,
)
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    OrderType,
    Participant,
    ParticipantDetails,
    ParticipantPositionSummary,
    ParticipantSummary,
    RequestForOrder,
    Side,
)


def test_add_instrument_returns_the_added_instrument() -> None:
    exchange = Exchange(time=lambda: 100)
    executor = Executor(exchange)

    response = executor.execute(AddInstrument(symbol="AAPL"))

    assert response == AddInstrumentResponse(instrument=Instrument(symbol="AAPL"))


def test_add_duplicate_instrument_returns_error() -> None:
    exchange = Exchange(time=lambda: 100)
    executor = Executor(exchange)
    executor.execute(AddInstrument(symbol="AAPL"))

    response = executor.execute(AddInstrument(symbol="AAPL"))

    assert isinstance(response, ErrorResponse)
    assert response.message.startswith("Failed to add instrument:")


def test_show_time_returns_exchange_time() -> None:
    executor = Executor(Exchange(time=lambda: 123))

    response = executor.execute(ShowTime())

    assert response == ShowTimeResponse(timestamp=123)


def test_list_instruments_returns_registered_symbols() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_instrument(Instrument(symbol="AAPL"))
    exchange.add_instrument(Instrument(symbol="MSFT"))

    response = Executor(exchange).execute(ListInstruments())

    assert response == ListInstrumentsResponse(symbols=("AAPL", "MSFT"))


def test_list_participants_returns_registered_ids_and_balances() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_participant(Participant("ALICE", "Alice", balance=123_45))
    exchange.add_participant(Participant("BOB", "Bob", balance=67_89))

    response = Executor(exchange).execute(ListParticipants())

    assert response == ListParticipantsResponse(
        participants=(
            ParticipantSummary(participant_id="ALICE", balance=123_45),
            ParticipantSummary(participant_id="BOB", balance=67_89),
        )
    )


def test_show_participant_returns_available_and_reserved_assets() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_instrument(Instrument(symbol="AAPL"))
    exchange.add_participant(
        Participant("ALICE", "Alice", balance=1_000, positions={"AAPL": 10})
    )
    exchange.place_order(
        RequestForOrder(
            participant_id="ALICE",
            symbol="AAPL",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            original_quantity=3,
            price_ticks=100,
        )
    )
    exchange.place_order(
        RequestForOrder(
            participant_id="ALICE",
            symbol="AAPL",
            side=Side.SELL,
            order_type=OrderType.LIMIT,
            original_quantity=4,
            price_ticks=200,
        )
    )

    response = Executor(exchange).execute(ShowParticipant(participant_id="ALICE"))

    assert response == ShowParticipantResponse(
        participant=ParticipantDetails(
            participant_id="ALICE",
            display_name="Alice",
            available_cash=700,
            reserved_cash=300,
            positions=(
                ParticipantPositionSummary(
                    symbol="AAPL",
                    available_quantity=6,
                    reserved_quantity=4,
                ),
            ),
        )
    )


def test_show_unknown_participant_returns_error() -> None:
    response = Executor(Exchange(time=lambda: 100)).execute(
        ShowParticipant(participant_id="UNKNOWN")
    )

    assert isinstance(response, ErrorResponse)
    assert response.message.startswith("Failed to get participant:")


def test_show_graph_returns_trades_for_requested_symbol() -> None:
    timestamp = iter(range(100, 200)).__next__
    exchange = Exchange(time=timestamp)
    exchange.add_instrument(Instrument(symbol="AAPL"))
    exchange.add_instrument(Instrument(symbol="MSFT"))
    exchange.add_participant(Participant("buyer", "Buyer", balance=10_000))
    exchange.add_participant(
        Participant(
            "seller",
            "Seller",
            positions={"AAPL": 2, "MSFT": 2},
        )
    )

    for symbol, price_ticks in (("AAPL", 100), ("MSFT", 200)):
        exchange.place_order(
            RequestForOrder(
                participant_id="seller",
                symbol=symbol,
                side=Side.SELL,
                order_type=OrderType.LIMIT,
                original_quantity=1,
                price_ticks=price_ticks,
            )
        )
        exchange.place_order(
            RequestForOrder(
                participant_id="buyer",
                symbol=symbol,
                side=Side.BUY,
                order_type=OrderType.LIMIT,
                original_quantity=1,
                price_ticks=price_ticks,
            )
        )

    aapl_trade = exchange.get_trades_by_symbol("AAPL")[0]
    response = Executor(exchange).execute(ShowGraph(symbol="AAPL"))

    assert response == ShowGraphResponse(
        symbol="AAPL",
        entries=(
            GraphEntry(
                timestamp=aapl_trade.timestamp,
                price_ticks=100,
            ),
        ),
    )


def test_show_graph_returns_empty_history_for_instrument_without_trades() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_instrument(Instrument(symbol="AAPL"))

    response = Executor(exchange).execute(ShowGraph(symbol="AAPL"))

    assert response == ShowGraphResponse(symbol="AAPL", entries=())


def test_show_graph_returns_error_for_unknown_symbol() -> None:
    response = Executor(Exchange(time=lambda: 100)).execute(ShowGraph(symbol="AAPL"))

    assert isinstance(response, ErrorResponse)
    assert response.message.startswith("Failed to generate graph:")
