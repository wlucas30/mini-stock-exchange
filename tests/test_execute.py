from mini_stock_exchange.commands.command import (
    AddInstrument,
    FastForward,
    ListInstruments,
    ListParticipants,
    SetTimeMultiplier,
    ShowGraph,
    ShowParticipant,
    ShowTime,
)
from mini_stock_exchange.commands.execute import (
    AddInstrumentResponse,
    ErrorResponse,
    Executor,
    FastForwardResponse,
    GraphEntry,
    ListInstrumentsResponse,
    ListParticipantsResponse,
    SetTimeMultiplierResponse,
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
from mini_stock_exchange.simulation import Simulation, SimulationTime


def test_add_instrument_returns_the_added_instrument() -> None:
    simulation_time = SimulationTime(current_time=100)
    exchange = Exchange(time=lambda: simulation_time.current_time)
    exchange.add_participant(Participant("MAKER_1", "Maker 1", balance=10_000))
    exchange.add_participant(Participant("MAKER_2", "Maker 2", balance=10_000))
    simulation = Simulation(
        exchange,
        simulation_time,
        initial_position_holder_ids=("MAKER_1", "MAKER_2"),
    )
    executor = Executor(exchange, simulation)

    response = executor.execute(
        AddInstrument(symbol="AAPL", price_ticks=10000, volume=100)
    )

    assert response == AddInstrumentResponse(
        instrument=Instrument(symbol="AAPL", total_supply=100),
        price_ticks=10000,
    )
    assert exchange.get_book_snapshot("AAPL").asks == ()
    assert (
        exchange.get_participant_details("MAKER_1").positions[0].available_quantity
        == 50
    )
    assert (
        exchange.get_participant_details("MAKER_2").positions[0].available_quantity
        == 50
    )


def test_add_duplicate_instrument_returns_error() -> None:
    simulation_time = SimulationTime(current_time=100)
    exchange = Exchange(time=lambda: simulation_time.current_time)
    exchange.add_participant(Participant("MAKER", "Maker", balance=10_000))
    simulation = Simulation(
        exchange,
        simulation_time,
        initial_position_holder_ids=("MAKER",),
    )
    executor = Executor(exchange, simulation)
    command = AddInstrument(symbol="AAPL", price_ticks=10000, volume=100)
    executor.execute(command)

    response = executor.execute(command)

    assert isinstance(response, ErrorResponse)
    assert response.message.startswith("Failed to add instrument:")


def test_show_time_returns_exchange_time() -> None:
    executor = Executor(Exchange(time=lambda: 123))

    response = executor.execute(ShowTime())

    assert response == ShowTimeResponse(timestamp=123)


def test_set_time_multiplier_updates_simulation_clock() -> None:
    simulation_time = SimulationTime()
    exchange = Exchange(time=lambda: simulation_time.current_time)
    simulation = Simulation(exchange, simulation_time)
    executor = Executor(exchange, simulation)

    response = executor.execute(SetTimeMultiplier(multiplier=5))

    assert response == SetTimeMultiplierResponse(multiplier=5)
    simulation.advance()
    assert simulation_time.current_time == 5


def test_fast_forward_updates_simulation_clock() -> None:
    simulation_time = SimulationTime(current_time=10)
    exchange = Exchange(time=lambda: simulation_time.current_time)
    simulation = Simulation(exchange, simulation_time)
    executor = Executor(exchange, simulation)

    response = executor.execute(FastForward(delta=30))

    assert response == FastForwardResponse(timestamp=40)
    assert simulation_time.current_time == 40


def test_list_instruments_returns_registered_symbols() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))
    exchange.add_instrument(Instrument(symbol="MSFT", total_supply=200))

    response = Executor(exchange).execute(ListInstruments())

    assert response == ListInstrumentsResponse(
        instruments=(
            Instrument(symbol="AAPL", total_supply=100),
            Instrument(symbol="MSFT", total_supply=200),
        )
    )


def test_list_participants_returns_registered_ids_and_balances() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_participant(Participant("ALICE", "Alice", balance=123_45))
    exchange.add_participant(Participant("BOB", "Bob", balance=67_89))

    response = Executor(exchange).execute(ListParticipants())

    assert response == ListParticipantsResponse(
        participants=(
            ParticipantSummary(
                participant_id="ALICE", balance=123_45, net_worth=123_45
            ),
            ParticipantSummary(participant_id="BOB", balance=67_89, net_worth=67_89),
        )
    )


def test_show_participant_returns_available_and_reserved_assets() -> None:
    exchange = Exchange(time=lambda: 100)
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))
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
                    average_cost_ticks=None,
                    mark_price_ticks=150,
                ),
            ),
            unrealised_gain=None,
            net_worth=2_500,
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
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))
    exchange.add_instrument(Instrument(symbol="MSFT", total_supply=100))
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
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))

    response = Executor(exchange).execute(ShowGraph(symbol="AAPL"))

    assert response == ShowGraphResponse(symbol="AAPL", entries=())


def test_show_graph_returns_error_for_unknown_symbol() -> None:
    response = Executor(Exchange(time=lambda: 100)).execute(ShowGraph(symbol="AAPL"))

    assert isinstance(response, ErrorResponse)
    assert response.message.startswith("Failed to generate graph:")
