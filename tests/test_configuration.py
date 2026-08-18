from pathlib import Path

import pytest

from mini_stock_exchange.configuration import (
    EXCHANGE_MASTER_ID,
    DefaultInstrument,
    read_default_instruments,
    seed_exchange,
)
from mini_stock_exchange.exchange.exchange import Exchange
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


def test_seed_exchange_adds_instruments_master_and_initial_asks(
    tmp_path: Path,
) -> None:
    config = tmp_path / "instruments.csv"
    config.write_text(
        "symbol,starting_price_ticks,initial_quantity\nALPHA,1000,100\nBETA,2000,50\n",
        encoding="utf-8",
    )
    exchange = Exchange(time=lambda: 123)

    market_states = seed_exchange(exchange, config)

    assert exchange.get_instrument_symbols() == ("ALPHA", "BETA")
    assert exchange.get_participant_summaries()[0].participant_id == (
        EXCHANGE_MASTER_ID
    )
    assert exchange.get_participant_summaries()[0].balance == 0

    alpha_ask = exchange.get_book_snapshot("ALPHA").asks[0]
    assert alpha_ask.participant_id == EXCHANGE_MASTER_ID
    assert alpha_ask.price_ticks == 1000
    assert alpha_ask.remaining_quantity == 100

    beta_ask = exchange.get_book_snapshot("BETA").asks[0]
    assert beta_ask.price_ticks == 2000
    assert beta_ask.remaining_quantity == 50
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
