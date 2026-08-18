import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from mini_stock_exchange.agents import (
    FundamentalTrader,
    MarketMakerAgent,
    RandomNoiseTrader,
)
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
    FundamentalValueEstimator,
    MarketState,
    SimulationAgent,
    make_initial_market_state,
)

EXPECTED_COLUMNS = ("symbol", "starting_price_ticks", "initial_quantity")
EXPECTED_AGENT_COLUMNS = ("participant_id", "display_name", "balance", "strategy")
EXPECTED_POSITION_COLUMNS = ("participant_id", "symbol", "quantity")


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


@dataclass(frozen=True, kw_only=True)
class DefaultPosition:
    participant_id: ParticipantId
    symbol: Symbol
    quantity: Quantity


def _make_random_noise_trader(
    participant_id: ParticipantId,
    fundamental_value_estimator: FundamentalValueEstimator,
) -> SimulationAgent:
    return RandomNoiseTrader(participant_id=participant_id)


def _make_fundamental_trader(
    participant_id: ParticipantId,
    fundamental_value_estimator: FundamentalValueEstimator,
) -> SimulationAgent:
    return FundamentalTrader(
        participant_id=participant_id,
        fundamental_value_estimator=fundamental_value_estimator,
    )


def _make_market_maker(
    participant_id: ParticipantId,
    fundamental_value_estimator: FundamentalValueEstimator,
) -> SimulationAgent:
    return MarketMakerAgent(
        participant_id=participant_id,
        fundamental_value_estimator=fundamental_value_estimator,
    )


AGENT_FACTORIES: dict[
    str, Callable[[ParticipantId, FundamentalValueEstimator], SimulationAgent]
] = {
    "RandomNoise": _make_random_noise_trader,
    "Fundamental": _make_fundamental_trader,
    "MarketMaker": _make_market_maker,
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


def read_default_positions(path: Path) -> tuple[DefaultPosition, ...]:
    """Read initial participant position allocations from a CSV file."""
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if tuple(reader.fieldnames or ()) != EXPECTED_POSITION_COLUMNS:
            raise ValueError(
                "Default position CSV must have columns: "
                + ", ".join(EXPECTED_POSITION_COLUMNS)
            )

        positions: list[DefaultPosition] = []
        seen_allocations: set[tuple[ParticipantId, Symbol]] = set()
        for row_number, row in enumerate(reader, start=2):
            participant_id = row["participant_id"]
            symbol = row["symbol"]
            allocation = (participant_id, symbol)
            if allocation in seen_allocations:
                raise ValueError(
                    f"Row {row_number}: duplicate initial position for "
                    f"{participant_id} and {symbol}"
                )

            positions.append(
                DefaultPosition(
                    participant_id=participant_id,
                    symbol=symbol,
                    quantity=_parse_positive_integer(
                        row["quantity"],
                        "quantity",
                        row_number,
                    ),
                )
            )
            seen_allocations.add(allocation)

    return tuple(positions)


def seed_exchange(
    exchange: Exchange,
    instrument_path: Path,
    position_path: Path,
) -> tuple[MarketState, ...]:
    """Add configured instruments and allocate their initial supply."""
    instruments = read_default_instruments(instrument_path)
    positions = read_default_positions(position_path)
    instruments_by_symbol = {
        instrument.symbol: instrument for instrument in instruments
    }
    participant_ids = {
        participant.participant_id
        for participant in exchange.get_participant_summaries()
    }

    allocated_by_symbol: dict[Symbol, Quantity] = {}
    for position in positions:
        if position.participant_id not in participant_ids:
            raise ValueError(
                f"Initial position participant does not exist: "
                f"{position.participant_id}"
            )
        if position.symbol not in instruments_by_symbol:
            raise ValueError(
                f"Initial position symbol does not exist: {position.symbol}"
            )
        allocated_by_symbol[position.symbol] = (
            allocated_by_symbol.get(position.symbol, 0) + position.quantity
        )

    for instrument in instruments:
        allocated = allocated_by_symbol.get(instrument.symbol, 0)
        if allocated != instrument.initial_quantity:
            raise ValueError(
                f"Initial positions for {instrument.symbol} allocate {allocated} "
                f"of {instrument.initial_quantity} units"
            )

    market_states: list[MarketState] = []
    for instrument in instruments:
        exchange.add_instrument(Instrument(symbol=instrument.symbol))
        market_states.append(
            make_initial_market_state(
                symbol=instrument.symbol,
                fundamental_value_ticks=instrument.starting_price_ticks,
            )
        )

    for position in positions:
        instrument = instruments_by_symbol[position.symbol]
        exchange.allocate_initial_position(
            participant_id=position.participant_id,
            symbol=position.symbol,
            quantity=position.quantity,
            price_ticks=instrument.starting_price_ticks,
        )

    return tuple(market_states)


def seed_agents(
    exchange: Exchange,
    path: Path,
    fundamental_value_estimator: FundamentalValueEstimator,
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
        agents.append(
            AGENT_FACTORIES[agent.strategy](
                agent.participant_id,
                fundamental_value_estimator,
            )
        )

    return tuple(agents)
