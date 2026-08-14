import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mini_stock_exchange.agents import RandomNoiseTrader
from mini_stock_exchange.commands.lexer import KEYWORDS, is_identifier
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Cash,
    Instrument,
    Participant,
    ParticipantId,
    PriceTicks,
    Quantity,
    Symbol,
)
from mini_stock_exchange.simulation import (
    MarketState,
    SimulationAgent,
    make_initial_market_state,
)

EXCHANGE_MASTER_ID = "EXCHANGE_MASTER"
EXCHANGE_MASTER_NAME = "Exchange Master"
EXPECTED_COLUMNS = ("symbol", "starting_price_ticks", "initial_quantity")
EXPECTED_AGENT_COLUMNS = ("participant_id", "display_name", "balance", "strategy")


@dataclass(frozen=True, kw_only=True)
class DefaultInstrument:
    symbol: Symbol
    starting_price_ticks: PriceTicks
    initial_quantity: Quantity


@dataclass(frozen=True, kw_only=True)
class DefaultAgent:
    participant_id: ParticipantId
    display_name: str
    balance: Cash
    strategy: str


def _make_random_noise_trader(participant_id: ParticipantId) -> SimulationAgent:
    return RandomNoiseTrader(participant_id=participant_id)


AGENT_FACTORIES: dict[str, Callable[[ParticipantId], SimulationAgent]] = {
    "RandomNoise": _make_random_noise_trader,
}


def _parse_positive_integer(value: str, field: str, row_number: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValueError(f"Row {row_number}: {field} must be an integer") from error

    if parsed <= 0:
        raise ValueError(f"Row {row_number}: {field} must be positive")

    return parsed


def read_default_instruments(path: Path) -> tuple[DefaultInstrument, ...]:
    """Read and validate default instrument definitions from a CSV file."""
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if tuple(reader.fieldnames or ()) != EXPECTED_COLUMNS:
            raise ValueError(
                "Default instrument CSV must have columns: "
                + ", ".join(EXPECTED_COLUMNS)
            )

        instruments: list[DefaultInstrument] = []
        seen_symbols: set[Symbol] = set()

        for row_number, row in enumerate(reader, start=2):
            symbol = row["symbol"]
            if not is_identifier(symbol) or symbol in KEYWORDS:
                raise ValueError(f"Row {row_number}: invalid symbol {symbol!r}")
            if symbol in seen_symbols:
                raise ValueError(f"Row {row_number}: duplicate symbol {symbol}")

            instruments.append(
                DefaultInstrument(
                    symbol=symbol,
                    starting_price_ticks=_parse_positive_integer(
                        row["starting_price_ticks"],
                        "starting_price_ticks",
                        row_number,
                    ),
                    initial_quantity=_parse_positive_integer(
                        row["initial_quantity"],
                        "initial_quantity",
                        row_number,
                    ),
                )
            )
            seen_symbols.add(symbol)

    if not instruments:
        raise ValueError("Default instrument CSV must contain at least one instrument")

    return tuple(instruments)


def read_default_agents(path: Path) -> tuple[DefaultAgent, ...]:
    """Read and validate automated agent definitions from a CSV file."""
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if tuple(reader.fieldnames or ()) != EXPECTED_AGENT_COLUMNS:
            raise ValueError(
                "Default agent CSV must have columns: "
                + ", ".join(EXPECTED_AGENT_COLUMNS)
            )

        agents: list[DefaultAgent] = []
        seen_participant_ids: set[ParticipantId] = set()

        for row_number, row in enumerate(reader, start=2):
            participant_id = row["participant_id"]
            if not is_identifier(participant_id) or participant_id in KEYWORDS:
                raise ValueError(
                    f"Row {row_number}: invalid participant ID {participant_id!r}"
                )
            if participant_id in seen_participant_ids:
                raise ValueError(
                    f"Row {row_number}: duplicate participant ID {participant_id}"
                )

            display_name = row["display_name"].strip()
            if not display_name:
                raise ValueError(f"Row {row_number}: display_name cannot be empty")

            strategy = row["strategy"]
            if strategy not in AGENT_FACTORIES:
                raise ValueError(
                    f"Row {row_number}: unknown agent strategy {strategy!r}"
                )

            agents.append(
                DefaultAgent(
                    participant_id=participant_id,
                    display_name=display_name,
                    balance=_parse_positive_integer(
                        row["balance"],
                        "balance",
                        row_number,
                    ),
                    strategy=strategy,
                )
            )
            seen_participant_ids.add(participant_id)

    return tuple(agents)


def seed_exchange(exchange: Exchange, path: Path) -> tuple[MarketState, ...]:
    """Add configured instruments and initial Exchange Master sell orders."""
    instruments = read_default_instruments(path)
    exchange_master = Participant(
        participant_id=EXCHANGE_MASTER_ID,
        display_name=EXCHANGE_MASTER_NAME,
        balance=0,
        positions={},
    )

    exchange.add_participant(exchange_master)

    market_states: list[MarketState] = []
    for instrument in instruments:
        exchange.issue_instrument(
            instrument=Instrument(symbol=instrument.symbol),
            issuer_id=EXCHANGE_MASTER_ID,
            price_ticks=instrument.starting_price_ticks,
            volume=instrument.initial_quantity,
        )
        market_states.append(
            make_initial_market_state(
                symbol=instrument.symbol,
                fundamental_value_ticks=instrument.starting_price_ticks,
            )
        )

    return tuple(market_states)


def seed_agents(
    exchange: Exchange,
    path: Path,
) -> tuple[SimulationAgent, ...]:
    """Create configured participant accounts and automated agents."""
    agents: list[SimulationAgent] = []

    for agent in read_default_agents(path):
        exchange.add_participant(
            Participant(
                participant_id=agent.participant_id,
                display_name=agent.display_name,
                balance=agent.balance,
            )
        )
        agents.append(AGENT_FACTORIES[agent.strategy](agent.participant_id))

    return tuple(agents)
