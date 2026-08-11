from collections.abc import Iterable
from typing import Protocol

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import Timestamp


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
    ) -> None:
        self._exchange = exchange
        self._time = simulation_time
        self._agents = list(agents)

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
