import csv
from dataclasses import dataclass
from pathlib import Path

from mini_stock_exchange.commands.lexer import KEYWORDS, is_identifier
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import (
    Instrument,
    Participant,
    PriceTicks,
    Quantity,
    Symbol,
)
from mini_stock_exchange.simulation import MarketState, make_initial_market_state

EXCHANGE_MASTER_ID = "EXCHANGE_MASTER"
EXCHANGE_MASTER_NAME = "Exchange Master"
EXPECTED_COLUMNS = ("symbol", "starting_price_ticks", "initial_quantity")


@dataclass(frozen=True, kw_only=True)
class DefaultInstrument:
    symbol: Symbol
    starting_price_ticks: PriceTicks
    initial_quantity: Quantity


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
