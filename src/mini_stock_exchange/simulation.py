from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    Order,
    ParticipantId,
    PriceTicks,
    Quantity,
    Symbol,
    Timestamp,
)


class Sentiment(Enum):
    BEARISH = auto()
    NEUTRAL = auto()
    BULLISH = auto()


@dataclass(kw_only=True)
class MarketState:
    """Hidden simulation state for one instrument."""

    symbol: Symbol
    fundamental_value_ticks: PriceTicks
    sentiment: Sentiment
    volatility: float

    def __post_init__(self) -> None:
        if self.fundamental_value_ticks <= 0:
            raise ValueError("Fundamental value must be positive")
        if self.volatility < 0:
            raise ValueError("Volatility cannot be negative")


def make_initial_market_state(
    symbol: Symbol,
    fundamental_value_ticks: PriceTicks,
) -> MarketState:
    """Create neutral hidden state using the standard initial volatility."""
    return MarketState(
        symbol=symbol,
        fundamental_value_ticks=fundamental_value_ticks,
        sentiment=Sentiment.NEUTRAL,
        volatility=max(1.0, fundamental_value_ticks * 0.001),
    )


class SimulationTime:
    """The clock owned by a Simulation."""

    def __init__(self, current_time: Timestamp = 0, multiplier: int = 1) -> None:
        if current_time < 0:
            raise ValueError("Current time cannot be negative")
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")

        self._current_time = current_time
        self._multiplier = multiplier

    @property
    def current_time(self) -> Timestamp:
        return self._current_time

    @property
    def multiplier(self) -> int:
        return self._multiplier

    @multiplier.setter
    def multiplier(self, value: int) -> None:
        if value < 0:
            raise ValueError("Multiplier cannot be negative")

        self._multiplier = value

    def step(self) -> Timestamp:
        """Advance the clock by exactly one simulation-time unit."""
        self._current_time += 1
        return self._current_time


class SimulationAgent(Protocol):
    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        """Perform the agent's action for one simulation step."""


class Simulation:
    """Coordinates the exchange with its SimulationTime."""

    def __init__(
        self,
        exchange: Exchange,
        simulation_time: SimulationTime,
        agents: Iterable[SimulationAgent] = (),
        market_states: Iterable[MarketState] = (),
    ) -> None:
        self._exchange = exchange
        self._time = simulation_time
        self._agents = list(agents)
        self._market_states: dict[Symbol, MarketState] = {}

        for market_state in market_states:
            if market_state.symbol in self._market_states:
                raise ValueError(f"Duplicate market state for {market_state.symbol}")
            if market_state.symbol not in exchange.get_instrument_symbols():
                raise ValueError(
                    f"Market state symbol {market_state.symbol} does not exist"
                )
            self._market_states[market_state.symbol] = market_state

        missing_states = (
            set(exchange.get_instrument_symbols()) - self._market_states.keys()
        )
        if missing_states:
            missing = ", ".join(sorted(missing_states))
            raise ValueError(f"Missing market state for instrument(s): {missing}")

    @property
    def exchange(self) -> Exchange:
        return self._exchange

    @property
    def current_time(self) -> Timestamp:
        return self._time.current_time

    @property
    def multiplier(self) -> int:
        return self._time.multiplier

    @multiplier.setter
    def multiplier(self, value: int) -> None:
        self._time.multiplier = value

    def issue_instrument(
        self,
        instrument: Instrument,
        issuer_id: ParticipantId,
        price_ticks: PriceTicks,
        volume: Quantity,
    ) -> Order:
        """Issue an instrument and create its initial hidden market state."""
        if instrument.symbol in self._market_states:
            raise ValueError(f"Market state already exists: {instrument.symbol}")

        order = self._exchange.issue_instrument(
            instrument=instrument,
            issuer_id=issuer_id,
            price_ticks=price_ticks,
            volume=volume,
        )
        self._market_states[instrument.symbol] = make_initial_market_state(
            symbol=instrument.symbol,
            fundamental_value_ticks=price_ticks,
        )
        return order

    def step(self) -> Timestamp:
        """Advance one unit and give every agent one opportunity to act."""
        timestamp = self._time.step()
        for agent in self._agents:
            agent.act(self._exchange, timestamp)
        return timestamp

    def advance(self) -> Timestamp:
        """Run one step per unit of the current multiplier."""
        for _ in range(self.multiplier):
            self.step()
        return self.current_time

    def fast_forward(self, delta: Timestamp) -> Timestamp:
        """Run every simulation step in a non-negative delta."""
        if delta < 0:
            raise ValueError("Fast-forward delta cannot be negative")

        for _ in range(delta):
            self.step()
        return self.current_time
