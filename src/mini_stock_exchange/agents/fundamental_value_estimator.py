import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field

from mini_stock_exchange.exchange.models import PriceTicks, Symbol, Timestamp

type FundamentalValueEstimatorFactory = Callable[[], FundamentalValueEstimator]
type FundamentalValueProvider = Callable[[Symbol], PriceTicks]


INITIAL_NOISE_MEAN = 0.0
INITIAL_NOISE_STD_DEV = 0.01

NOISE_STD_DEV = 0.01
NOISE_HALF_LIFE_STEPS = 1_000


class _EstimateState:
    def __init__(self, initial_timestamp: Timestamp) -> None:
        self._noise_fraction: float = random.gauss(
            INITIAL_NOISE_MEAN,
            INITIAL_NOISE_STD_DEV,
        )
        self._timestamp = initial_timestamp

    def get_noise(self, timestamp: Timestamp) -> float:
        """Get the noise fraction at the given timestamp."""
        if timestamp < self._timestamp:
            raise ValueError("Timestamp must not be in the past")

        elapsed = timestamp - self._timestamp
        if elapsed == 0:
            return self._noise_fraction

        persistence = 0.5 ** (elapsed / NOISE_HALF_LIFE_STEPS)

        innovation_std_dev = NOISE_STD_DEV * math.sqrt(1 - persistence**2)

        self._noise_fraction = persistence * self._noise_fraction + random.gauss(
            0, innovation_std_dev
        )

        self._timestamp = timestamp

        return self._noise_fraction


def _empty_estimate_states() -> dict[Symbol, _EstimateState]:
    return {}


@dataclass(kw_only=True)
class FundamentalValueEstimator:
    """Maintains one agent's estimates of hidden fundamental values."""

    fundamental_value_provider: FundamentalValueProvider
    initial_timestamp: Timestamp
    _states: dict[Symbol, _EstimateState] = field(
        default_factory=_empty_estimate_states,
        init=False,
        repr=False,
    )

    def _get_state(self, symbol: Symbol) -> _EstimateState:
        state = self._states.get(symbol)
        if state is None:
            state = _EstimateState(self.initial_timestamp)
            self._states[symbol] = state
        return state

    def estimate(self, symbol: Symbol, timestamp: Timestamp) -> PriceTicks:
        """Return this agent's estimate for an instrument's fundamental value."""
        fundamental_value = self.fundamental_value_provider(symbol)
        noise_fraction = self._get_state(symbol).get_noise(timestamp)
        return max(1, round(fundamental_value * (1 + noise_fraction)))
