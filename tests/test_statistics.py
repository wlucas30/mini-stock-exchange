import pytest

from mini_stock_exchange.exchange.models import Trade
from mini_stock_exchange.exchange.order_book import BookEntry, BookSnapshot
from mini_stock_exchange.simulation import PriceHistoryEntry
from mini_stock_exchange.statistics import calculate_instrument_statistics


def test_calculates_statistics_over_last_thousand_steps() -> None:
    trades = (
        Trade(1, 1, "AAPL", 90, 10, 1, 2, "BUYER", "SELLER", 500),
        Trade(2, 2, "AAPL", 110, 2, 3, 4, "BUYER", "SELLER", 501),
        Trade(3, 3, "AAPL", 130, 1, 5, 6, "BUYER", "SELLER", 1500),
    )
    book = BookSnapshot(
        symbol="AAPL",
        bids=(
            BookEntry(
                order_id=1,
                participant_id="BUYER",
                price_ticks=99,
                remaining_quantity=1,
                sequence=1,
                timestamp=1500,
            ),
        ),
        asks=(
            BookEntry(
                order_id=2,
                participant_id="SELLER",
                price_ticks=101,
                remaining_quantity=1,
                sequence=2,
                timestamp=1500,
            ),
        ),
    )
    midpoint_history = (
        PriceHistoryEntry(timestamp=500, price_ticks=100),
        PriceHistoryEntry(timestamp=501, price_ticks=110),
        PriceHistoryEntry(timestamp=502, price_ticks=121),
    )

    result = calculate_instrument_statistics(
        symbol="AAPL",
        current_time=1500,
        trades=trades,
        book=book,
        midpoint_history=midpoint_history,
    )

    assert result.window_start == 501
    assert result.window_end == 1500
    assert result.last_trade_price_ticks == 130
    assert result.midpoint_ticks == 100
    assert result.spread_ticks == 2
    assert result.spread_percent == pytest.approx(2.0)
    assert result.trade_count == 2
    assert result.traded_volume == 3
    assert result.vwap_ticks == pytest.approx(350 / 3)
    assert result.midpoint_volatility == pytest.approx(0.0)
