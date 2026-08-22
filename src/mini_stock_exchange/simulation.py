import math
import random
from array import array
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Cash,
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
MIN_VOLATILITY = 0.00125
MAX_VOLATILITY = 0.0225
NORMAL_VOLATILITY = 0.0075
VOLATILITY_PERSISTENCE = 0.99
VOLATILITY_SHOCK_STD_DEV = 0.00005
SENTIMENT_BIAS_FACTOR = 0.25
VOLATILITY_PERIOD_STEPS = 1_000
GROWTH_RATE_PERSISTENCE = 0.99


type ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True, kw_only=True)
class PriceHistoryEntry:
    """A price observed at one simulation timestamp."""

    timestamp: Timestamp
    price_ticks: PriceTicks


@dataclass(frozen=True, kw_only=True)
class ParticipantPerformanceHistory:
    """Stored cash and net-worth series for one participant."""

    participant_id: ParticipantId
    start_timestamp: Timestamp
    cash_balances: tuple[Cash, ...]
    net_worths: tuple[Cash, ...]


def _empty_cash_array() -> array[int]:
    return array("q")


@dataclass(kw_only=True)
class _ParticipantPerformanceHistory:
    start_timestamp: Timestamp
    cash_balances: array[int] = field(default_factory=_empty_cash_array)
    net_worths: array[int] = field(default_factory=_empty_cash_array)

    def append(
        self,
        timestamp: Timestamp,
        cash_balance: Cash,
        net_worth: Cash,
    ) -> None:
        expected_timestamp = self.start_timestamp + len(self.cash_balances)
        if timestamp != expected_timestamp:
            raise RuntimeError("Participant performance timestamps must be consecutive")

        self.cash_balances.append(cash_balance)
        self.net_worths.append(net_worth)


@dataclass(kw_only=True)
class MarketState:
    """Hidden simulation state for one instrument."""

    symbol: Symbol
    fundamental_value_ticks: PriceTicks
    sentiment: Sentiment
    volatility: float
    _fundamental_value: float = field(init=False, repr=False)
    _growth_rate: float = field(init=False, repr=False, default=0.0)

    def __post_init__(self) -> None:
        if self.fundamental_value_ticks <= 0:
            raise ValueError("Fundamental value must be positive")
        if self.volatility < 0:
            raise ValueError("Volatility cannot be negative")

        self._fundamental_value = float(self.fundamental_value_ticks)

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
        target_growth_rate = (
            sentiment_direction * self.volatility * SENTIMENT_BIAS_FACTOR
        )
        self._growth_rate = target_growth_rate + GROWTH_RATE_PERSISTENCE * (
            self._growth_rate - target_growth_rate
        )

        step_growth_rate = self._growth_rate / VOLATILITY_PERIOD_STEPS
        step_volatility = self.volatility / math.sqrt(VOLATILITY_PERIOD_STEPS)
        log_value = math.log(self._fundamental_value)
        log_movement = random.gauss(
            step_growth_rate,
            step_volatility,
        )
        self._fundamental_value = math.exp(log_value + log_movement)
        self.fundamental_value_ticks = max(1, round(self._fundamental_value))


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
                PriceHistoryEntry(
                    timestamp=self._time.current_time,
                    price_ticks=market_state.fundamental_value_ticks,
                )
            ]
            for symbol, market_state in self._market_states.items()
        }
        self._midpoint_history: dict[Symbol, list[PriceHistoryEntry]] = {
            symbol: [] for symbol in self._market_states
        }
        self._participant_performance_histories: dict[
            ParticipantId, _ParticipantPerformanceHistory
        ] = {}
        self._record_participant_performance(self._time.current_time)

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
            PriceHistoryEntry(
                timestamp=self._time.current_time,
                price_ticks=price_ticks,
            )
        ]
        self._midpoint_history[instrument.symbol] = []

    def get_fundamental_value_history(
        self,
        symbol: Symbol,
    ) -> tuple[PriceHistoryEntry, ...]:
        """Return the exact fundamental-value history for one instrument."""
        try:
            history = self._fundamental_value_history[symbol]
        except KeyError as error:
            raise ValueError(f"Symbol {symbol} does not exist") from error
        return tuple(history)

    def get_midpoint_history(
        self,
        symbol: Symbol,
    ) -> tuple[PriceHistoryEntry, ...]:
        """Return the order-book midpoint history for one instrument."""
        try:
            history = self._midpoint_history[symbol]
        except KeyError as error:
            raise ValueError(f"Symbol {symbol} does not exist") from error
        return tuple(history)

    def get_participant_performance_history(
        self,
        participant_id: ParticipantId,
    ) -> ParticipantPerformanceHistory:
        """Return stored cash and net-worth history for one participant."""
        try:
            history = self._participant_performance_histories[participant_id]
        except KeyError as error:
            raise ValueError(
                f"Participant {participant_id} has no performance history"
            ) from error

        return ParticipantPerformanceHistory(
            participant_id=participant_id,
            start_timestamp=history.start_timestamp,
            cash_balances=tuple(history.cash_balances),
            net_worths=tuple(history.net_worths),
        )

    def _record_participant_performance(self, timestamp: Timestamp) -> None:
        for valuation in self._exchange.get_participant_valuations():
            history = self._participant_performance_histories.get(
                valuation.participant_id
            )
            if history is None:
                history = _ParticipantPerformanceHistory(start_timestamp=timestamp)
                self._participant_performance_histories[valuation.participant_id] = (
                    history
                )
            history.append(
                timestamp=timestamp,
                cash_balance=valuation.cash_balance,
                net_worth=valuation.net_worth,
            )

    def step(self) -> Timestamp:
        """Advance one unit and give every agent one opportunity to act."""
        timestamp = self._time.step()
        self._exchange.expire_orders(timestamp)
        for market_state in self._market_states.values():
            market_state.step()
            self._fundamental_value_history[market_state.symbol].append(
                PriceHistoryEntry(
                    timestamp=timestamp,
                    price_ticks=market_state.fundamental_value_ticks,
                )
            )
        for agent in self._agents:
            agent.act(self._exchange, timestamp)
        for symbol in self._market_states:
            book = self._exchange.get_book_snapshot(symbol)
            if book.bids and book.asks:
                midpoint = (book.bids[0].price_ticks + book.asks[0].price_ticks) // 2
                self._midpoint_history[symbol].append(
                    PriceHistoryEntry(
                        timestamp=timestamp,
                        price_ticks=midpoint,
                    )
                )
        self._record_participant_performance(timestamp)
        return timestamp

    def advance(self) -> Timestamp:
        """Run one step per unit of the current multiplier."""
        for _ in range(self.multiplier):
            self.step()
        return self.current_time

    def fast_forward(
        self,
        delta: Timestamp,
        progress_callback: ProgressCallback | None = None,
    ) -> Timestamp:
        """Run every simulation step in a non-negative delta."""
        if delta < 0:
            raise ValueError("Fast-forward delta cannot be negative")

        progress_interval = max(1, delta // 100)
        for completed in range(1, delta + 1):
            self.step()
            if progress_callback is not None and (
                completed % progress_interval == 0 or completed == delta
            ):
                progress_callback(completed, delta)
        return self.current_time
