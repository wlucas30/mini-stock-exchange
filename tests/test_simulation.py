# pyright: reportPrivateUsage=false

from collections.abc import Callable

import pytest

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    OrderStatus,
    OrderType,
    Participant,
    RequestForOrder,
    Side,
    Timestamp,
)
from mini_stock_exchange.simulation import (
    MarketState,
    Sentiment,
    Simulation,
    SimulationTime,
)


class RecordingAgent:
    def __init__(self) -> None:
        self.timestamps: list[Timestamp] = []

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        self.timestamps.append(timestamp)


def make_simulation(
    *,
    current_time: Timestamp = 0,
    multiplier: int = 1,
    agents: tuple[RecordingAgent, ...] = (),
) -> tuple[Simulation, SimulationTime]:
    simulation_time = SimulationTime(
        current_time=current_time,
        multiplier=multiplier,
    )
    exchange = Exchange(time=lambda: simulation_time.current_time)
    return Simulation(exchange, simulation_time, agents), simulation_time


def test_step_advances_once_and_invokes_agents() -> None:
    agent = RecordingAgent()
    simulation, simulation_time = make_simulation(
        current_time=10,
        multiplier=3,
        agents=(agent,),
    )

    result = simulation.step()

    assert result == 11
    assert simulation_time.current_time == 11
    assert agent.timestamps == [11]


def test_step_expires_due_limit_order_and_releases_reserved_cash() -> None:
    simulation_time = SimulationTime(current_time=10)
    exchange = Exchange(time=lambda: simulation_time.current_time)
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))
    exchange.add_participant(Participant("BUYER", "Buyer", balance=1_000))
    simulation = Simulation(
        exchange,
        simulation_time,
        market_states={
            "AAPL": MarketState(
                symbol="AAPL",
                fundamental_value_ticks=100,
                sentiment=Sentiment.NEUTRAL,
                volatility=0.001,
            )
        },
    )
    order = exchange.place_order(
        RequestForOrder(
            participant_id="BUYER",
            symbol="AAPL",
            side=Side.BUY,
            order_type=OrderType.LIMIT,
            original_quantity=5,
            price_ticks=100,
            expires_at=11,
        )
    )

    simulation.step()

    assert order.status is OrderStatus.CANCELLED
    assert exchange.get_participant_details("BUYER").available_cash == 1_000


def test_advance_runs_one_step_per_multiplier_unit() -> None:
    agent = RecordingAgent()
    simulation, _ = make_simulation(
        current_time=10,
        multiplier=3,
        agents=(agent,),
    )

    result = simulation.advance()

    assert result == 13
    assert agent.timestamps == [11, 12, 13]


def test_multiplier_can_pause_and_resume_time() -> None:
    simulation, _ = make_simulation(current_time=10)

    simulation.multiplier = 0
    simulation.advance()
    assert simulation.current_time == 10

    simulation.multiplier = 4
    simulation.advance()
    assert simulation.current_time == 14


def test_fast_forward_runs_every_intermediate_step() -> None:
    agent = RecordingAgent()
    simulation, _ = make_simulation(
        current_time=10,
        multiplier=5,
        agents=(agent,),
    )

    result = simulation.fast_forward(3)

    assert result == 13
    assert agent.timestamps == [11, 12, 13]


def test_issue_instrument_creates_hidden_market_state() -> None:
    simulation, _ = make_simulation()
    simulation.exchange.add_participant(
        Participant("MARKET_MAKER", "Market Maker", balance=0)
    )

    market_states: dict[str, MarketState] = {}
    simulation = Simulation(
        simulation.exchange,
        SimulationTime(),
        market_states=market_states,
        initial_position_holder_ids=("MARKET_MAKER",),
    )

    simulation.issue_instrument(
        instrument=Instrument(symbol="AAPL", total_supply=100),
        price_ticks=10_000,
    )

    assert market_states == {
        "AAPL": MarketState(
            symbol="AAPL",
            fundamental_value_ticks=10_000,
            sentiment=Sentiment.NEUTRAL,
            volatility=0.001,
        )
    }


def test_simulation_requires_market_state_for_existing_instrument() -> None:
    simulation_time = SimulationTime()
    exchange = Exchange(time=lambda: simulation_time.current_time)
    exchange.add_instrument(Instrument(symbol="AAPL", total_supply=100))

    with pytest.raises(ValueError, match="Missing market state for instrument"):
        Simulation(exchange, simulation_time)


@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (lambda: SimulationTime(current_time=-1), "Current time cannot be negative"),
        (lambda: SimulationTime(multiplier=-1), "Multiplier cannot be negative"),
        (
            lambda: make_simulation()[0].fast_forward(-1),
            "Fast-forward delta cannot be negative",
        ),
    ],
)
def test_rejects_negative_values(
    operation: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        operation()
