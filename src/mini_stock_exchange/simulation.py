import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    ParticipantId,
    PriceTicks,
    Symbol,
    Timestamp,
)


class Sentiment(Enum):
    BEARISH = auto()
    NEUTRAL = auto()
    BULLISH = auto()


SENTIMENT_CHANGE_PROBABILITY = 0.02
MIN_VOLATILITY = 0.0001
MAX_VOLATILITY = 0.005
NORMAL_VOLATILITY = 0.001
VOLATILITY_PERSISTENCE = 0.99
VOLATILITY_SHOCK_STD_DEV = 0.00005
SENTIMENT_BIAS_FACTOR = 0.25
FUNDAMENTAL_ESTIMATE_ERROR = 0.03


type FundamentalValueEstimator = Callable[[Symbol], PriceTicks]


@dataclass(frozen=True, kw_only=True)
class FundamentalValueEntry:
    """The exact hidden fundamental value at one simulation timestamp."""

    timestamp: Timestamp
    price_ticks: PriceTicks


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

    def step(self) -> None:
        """Randomly evolve sentiment, volatility, and fundamental value."""
        if random.random() < SENTIMENT_CHANGE_PROBABILITY:
            alternatives = tuple(
                sentiment for sentiment in Sentiment if sentiment is not self.sentiment
            )
            self.sentiment = random.choice(alternatives)

        volatility_change = random.gauss(
            0,
            VOLATILITY_SHOCK_STD_DEV,
        )
        mean_reverting_volatility = NORMAL_VOLATILITY + VOLATILITY_PERSISTENCE * (
            self.volatility - NORMAL_VOLATILITY
        )
        self.volatility = min(
            MAX_VOLATILITY,
            max(MIN_VOLATILITY, mean_reverting_volatility + volatility_change),
        )

        sentiment_direction = {
            Sentiment.BEARISH: -1,
            Sentiment.NEUTRAL: 0,
            Sentiment.BULLISH: 1,
        }[self.sentiment]
        mean_movement = sentiment_direction * self.volatility * SENTIMENT_BIAS_FACTOR
        percentage_movement = random.gauss(mean_movement, self.volatility)
        new_value = round(self.fundamental_value_ticks * (1 + percentage_movement))
        self.fundamental_value_ticks = max(1, new_value)

    @property
    def fundamental_value_estimate(self) -> PriceTicks:
        std_dev = max(1.0, self.fundamental_value_ticks * FUNDAMENTAL_ESTIMATE_ERROR)

        return max(
            1,
            round(
                random.gauss(
                    self.fundamental_value_ticks,
                    std_dev,
                )
            ),
        )


def make_initial_market_state(
    symbol: Symbol,
    fundamental_value_ticks: PriceTicks,
) -> MarketState:
    """Create neutral hidden state using the standard initial volatility."""
    return MarketState(
        symbol=symbol,
        fundamental_value_ticks=fundamental_value_ticks,
        sentiment=Sentiment.NEUTRAL,
        volatility=0.001,
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
        market_states: dict[Symbol, MarketState] | None = None,
        initial_position_holder_ids: Iterable[ParticipantId] = (),
    ) -> None:
        self._exchange = exchange
        self._time = simulation_time
        self._agents = list(agents)
        self._initial_position_holder_ids = tuple(initial_position_holder_ids)
        self._market_states = market_states if market_states is not None else {}

        for symbol, market_state in self._market_states.items():
            if symbol != market_state.symbol:
                raise ValueError(f"Market state key does not match symbol: {symbol}")
            if market_state.symbol not in exchange.get_instrument_symbols():
                raise ValueError(
                    f"Market state symbol {market_state.symbol} does not exist"
                )

        missing_states = (
            set(exchange.get_instrument_symbols()) - self._market_states.keys()
        )
        if missing_states:
            missing = ", ".join(sorted(missing_states))
            raise ValueError(f"Missing market state for instrument(s): {missing}")

        self._fundamental_value_history = {
            symbol: [
                FundamentalValueEntry(
                    timestamp=self._time.current_time,
                    price_ticks=market_state.fundamental_value_ticks,
                )
            ]
            for symbol, market_state in self._market_states.items()
        }

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
        price_ticks: PriceTicks,
    ) -> None:
        """Allocate a new instrument across the initial position holders."""
        if instrument.symbol in self._market_states:
            raise ValueError(f"Market state already exists: {instrument.symbol}")
        if not self._initial_position_holder_ids:
            raise ValueError("No participants are configured to receive new supply")
        if price_ticks <= 0:
            raise ValueError("Issue price must be positive")

        participant_ids = {
            participant.participant_id
            for participant in self._exchange.get_participant_summaries()
        }
        unknown_holders = set(self._initial_position_holder_ids) - participant_ids
        if unknown_holders:
            unknown = ", ".join(sorted(unknown_holders))
            raise ValueError(f"Initial position holder(s) do not exist: {unknown}")

        self._exchange.add_instrument(instrument)
        base_quantity, remainder = divmod(
            instrument.total_supply,
            len(self._initial_position_holder_ids),
        )
        for index, participant_id in enumerate(self._initial_position_holder_ids):
            quantity = base_quantity + (1 if index < remainder else 0)
            if quantity == 0:
                continue
            self._exchange.allocate_initial_position(
                participant_id=participant_id,
                symbol=instrument.symbol,
                quantity=quantity,
                price_ticks=price_ticks,
            )

        self._market_states[instrument.symbol] = make_initial_market_state(
            symbol=instrument.symbol,
            fundamental_value_ticks=price_ticks,
        )
        self._fundamental_value_history[instrument.symbol] = [
            FundamentalValueEntry(
                timestamp=self._time.current_time,
                price_ticks=price_ticks,
            )
        ]

    def get_fundamental_value_history(
        self,
        symbol: Symbol,
    ) -> tuple[FundamentalValueEntry, ...]:
        """Return the exact fundamental-value history for one instrument."""
        try:
            history = self._fundamental_value_history[symbol]
        except KeyError as error:
            raise ValueError(f"Symbol {symbol} does not exist") from error
        return tuple(history)

    def step(self) -> Timestamp:
        """Advance one unit and give every agent one opportunity to act."""
        timestamp = self._time.step()
        self._exchange.expire_orders(timestamp)
        for market_state in self._market_states.values():
            market_state.step()
            self._fundamental_value_history[market_state.symbol].append(
                FundamentalValueEntry(
                    timestamp=timestamp,
                    price_ticks=market_state.fundamental_value_ticks,
                )
            )
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
