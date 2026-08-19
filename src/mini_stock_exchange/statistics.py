from dataclasses import dataclass
from itertools import pairwise
from math import log
from statistics import stdev

from mini_stock_exchange.exchange.models import (
    PriceTicks,
    Quantity,
    Symbol,
    Timestamp,
    Trade,
)
from mini_stock_exchange.exchange.order_book import BookSnapshot
from mini_stock_exchange.simulation import PriceHistoryEntry

STATISTICS_WINDOW = 1_000


@dataclass(frozen=True, kw_only=True)
class InstrumentStatistics:
    """Observed market statistics over a fixed simulation-time window."""

    symbol: Symbol
    window_start: Timestamp
    window_end: Timestamp
    last_trade_price_ticks: PriceTicks | None
    midpoint_ticks: PriceTicks | None
    spread_ticks: PriceTicks | None
    spread_percent: float | None
    trade_count: int
    traded_volume: Quantity
    vwap_ticks: float | None
    midpoint_volatility: float | None


def calculate_instrument_statistics(
    *,
    symbol: Symbol,
    current_time: Timestamp,
    trades: tuple[Trade, ...],
    book: BookSnapshot,
    midpoint_history: tuple[PriceHistoryEntry, ...],
) -> InstrumentStatistics:
    """Calculate market statistics."""
    window_start = max(0, current_time - STATISTICS_WINDOW + 1)
    window_trades = tuple(
        trade for trade in trades if window_start <= trade.timestamp <= current_time
    )

    traded_volume = sum(trade.quantity for trade in window_trades)
    vwap_ticks = (
        sum(trade.price_ticks * trade.quantity for trade in window_trades)
        / traded_volume
        if traded_volume > 0
        else None
    )
    last_trade_price_ticks = window_trades[-1].price_ticks if window_trades else None

    if book.bids and book.asks:
        best_bid = book.bids[0].price_ticks
        best_ask = book.asks[0].price_ticks
        midpoint_ticks = (best_bid + best_ask) // 2
        spread_ticks = best_ask - best_bid
        spread_percent = spread_ticks / midpoint_ticks * 100
    else:
        midpoint_ticks = None
        spread_ticks = None
        spread_percent = None

    history_start = max(0, window_start - 1)
    window_midpoints = tuple(
        entry
        for entry in midpoint_history
        if history_start <= entry.timestamp <= current_time
    )
    returns = [
        log(current.price_ticks / previous.price_ticks)
        for previous, current in pairwise(window_midpoints)
        if current.timestamp == previous.timestamp + 1
        and current.timestamp >= window_start
    ]
    midpoint_volatility = stdev(returns) if len(returns) >= 2 else None

    return InstrumentStatistics(
        symbol=symbol,
        window_start=window_start,
        window_end=current_time,
        last_trade_price_ticks=last_trade_price_ticks,
        midpoint_ticks=midpoint_ticks,
        spread_ticks=spread_ticks,
        spread_percent=spread_percent,
        trade_count=len(window_trades),
        traded_volume=traded_volume,
        vwap_ticks=vwap_ticks,
        midpoint_volatility=midpoint_volatility,
    )
