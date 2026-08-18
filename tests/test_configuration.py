from pathlib import Path

import pytest

from mini_stock_exchange.configuration import (
    DefaultInstrument,
    read_default_instruments,
    seed_exchange,
)
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import Participant
from mini_stock_exchange.simulation import MarketState, Sentiment


def test_repository_default_instruments() -> None:
    config = Path(__file__).parents[1] / "config" / "default_instruments.csv"

    assert read_default_instruments(config) == (
        DefaultInstrument(
            symbol="ALPHA",
            starting_price_ticks=1000,
            initial_quantity=2000,
        ),
        DefaultInstrument(
            symbol="BETA",
            starting_price_ticks=2000,
            initial_quantity=2000,
        ),
        DefaultInstrument(
            symbol="GAMMA",
            starting_price_ticks=3000,
            initial_quantity=2000,
        ),
    )


def test_seed_exchange_allocates_configured_initial_positions(
    tmp_path: Path,
) -> None:
    instruments = tmp_path / "instruments.csv"
    instruments.write_text(
        "symbol,starting_price_ticks,initial_quantity\nALPHA,1000,100\nBETA,2000,50\n",
        encoding="utf-8",
    )
    positions = tmp_path / "positions.csv"
    positions.write_text(
        "participant_id,symbol,quantity\n"
        "MAKER_1,ALPHA,50\n"
        "MAKER_2,ALPHA,50\n"
        "MAKER_1,BETA,25\n"
        "MAKER_2,BETA,25\n",
        encoding="utf-8",
    )
    exchange = Exchange(time=lambda: 123)
    exchange.add_participant(Participant("MAKER_1", "Maker 1"))
    exchange.add_participant(Participant("MAKER_2", "Maker 2"))

    market_states = seed_exchange(exchange, instruments, positions)

    assert exchange.get_instrument_symbols() == ("ALPHA", "BETA")
    assert exchange.get_book_snapshot("ALPHA").asks == ()
    assert exchange.get_book_snapshot("BETA").asks == ()

    maker_1 = exchange.get_participant_details("MAKER_1")
    assert tuple(
        (position.symbol, position.total_quantity) for position in maker_1.positions
    ) == (("ALPHA", 50), ("BETA", 25))
    assert market_states == (
        MarketState(
            symbol="ALPHA",
            fundamental_value_ticks=1000,
            sentiment=Sentiment.NEUTRAL,
            volatility=0.001,
        ),
        MarketState(
            symbol="BETA",
            fundamental_value_ticks=2000,
            sentiment=Sentiment.NEUTRAL,
            volatility=0.001,
        ),
    )


@pytest.mark.parametrize(
    "contents",
    [
        "symbol,starting_price_ticks,initial_quantity\n",
        "symbol,starting_price_ticks,initial_quantity\nALPHA,0,100\n",
        "symbol,starting_price_ticks,initial_quantity\nalpha,1000,100\n",
        (
            "symbol,starting_price_ticks,initial_quantity\n"
            "ALPHA,1000,100\nALPHA,2000,100\n"
        ),
    ],
)
def test_rejects_invalid_default_instrument_config(
    tmp_path: Path,
    contents: str,
) -> None:
    config = tmp_path / "instruments.csv"
    config.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError):
        read_default_instruments(config)
