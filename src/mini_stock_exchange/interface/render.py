"""Convert ExecutorResponse values into plaintext and graphical responses."""

# pyright: reportUnknownMemberType=false

from dataclasses import dataclass

from matplotlib import pyplot as plt
from matplotlib.figure import Figure
from tabulate import tabulate

from mini_stock_exchange.commands.execute import (
    AddInstrumentResponse,
    AddParticipantResponse,
    CancelOrderResponse,
    ErrorResponse,
    ExecutorResponse,
    FastForwardResponse,
    GraphEntry,
    ListInstrumentsResponse,
    ListParticipantsResponse,
    PlaceOrderResponse,
    SetTimeMultiplierResponse,
    ShowBookResponse,
    ShowGraphResponse,
    ShowParticipantResponse,
    ShowPerformanceResponse,
    ShowStatsResponse,
    ShowTimeResponse,
    ShowTradesResponse,
)
from mini_stock_exchange.exchange.models import Cash, Symbol
from mini_stock_exchange.simulation import ParticipantPerformanceHistory

type RenderedOutput = TextOutput | FigureOutput


@dataclass(frozen=True, kw_only=True)
class TextOutput:
    text: str
    red: bool = False


@dataclass(frozen=True, kw_only=True)
class FigureOutput:
    figure: Figure


class Renderer:
    RED = "\033[31m"
    GREEN = "\033[32m"
    RESET = "\033[0m"

    @staticmethod
    def _format_cash(balance: Cash) -> str:
        sign = "-" if balance < 0 else ""
        dollars, cents = divmod(abs(balance), 100)
        return f"{sign}${dollars:,}.{cents:02d}"

    @classmethod
    def _format_gain(cls, gain: Cash | None) -> str:
        if gain is None:
            return "N/A"
        formatted = cls._format_cash(gain)
        if gain > 0:
            return f"{cls.GREEN}{formatted}{cls.RESET}"
        if gain < 0:
            return f"{cls.RED}{formatted}{cls.RESET}"
        return formatted

    @staticmethod
    def _generate_graph(
        symbol: Symbol,
        entries: tuple[GraphEntry, ...],
        fundamental_entries: tuple[GraphEntry, ...],
        midpoint_entries: tuple[GraphEntry, ...],
    ) -> Figure:
        figure, axes = plt.subplots(figsize=(8, 4.5), layout="constrained")

        axes.set_title(f"{symbol} price history")
        axes.set_xlabel("Simulation time")
        axes.set_ylabel("Price (ticks)")
        axes.grid(axis="both", alpha=0.3)

        if entries:
            axes.plot(
                [entry.timestamp for entry in entries],
                [entry.price_ticks for entry in entries],
                color="#0072B2",
                linewidth=1,
                label="Trade price",
            )

        if midpoint_entries:
            axes.plot(
                [entry.timestamp for entry in midpoint_entries],
                [entry.price_ticks for entry in midpoint_entries],
                color="#CC79A7",
                linewidth=1.5,
                linestyle="--",
                label="Book midpoint",
            )

        if fundamental_entries:
            axes.plot(
                [entry.timestamp for entry in fundamental_entries],
                [entry.price_ticks for entry in fundamental_entries],
                color="#E69F00",
                linewidth=1.5,
                label="Fundamental value",
            )

        if entries or midpoint_entries or fundamental_entries:
            axes.legend()
        else:
            axes.text(
                0.5,
                0.5,
                "No trades",
                horizontalalignment="center",
                verticalalignment="center",
                transform=axes.transAxes,
            )

        return figure

    @staticmethod
    def _generate_performance_graph(
        history: ParticipantPerformanceHistory,
    ) -> Figure:
        figure, axes = plt.subplots(figsize=(8, 4.5), layout="constrained")

        timestamps = range(
            history.start_timestamp,
            history.start_timestamp + len(history.cash_balances),
        )
        axes.plot(
            timestamps,
            [balance / 100 for balance in history.cash_balances],
            color="#0072B2",
            linewidth=1.25,
            label="Cash balance",
        )
        axes.plot(
            range(
                history.start_timestamp,
                history.start_timestamp + len(history.net_worths),
            ),
            [net_worth / 100 for net_worth in history.net_worths],
            color="#E69F00",
            linewidth=1.25,
            label="Net worth",
        )

        axes.set_title(f"{history.participant_id} performance")
        axes.set_xlabel("Simulation time")
        axes.set_ylabel("Value ($)")
        axes.grid(axis="both", alpha=0.3)
        axes.legend()
        return figure

    def render(self, response: ExecutorResponse) -> RenderedOutput:
        match response:
            case ErrorResponse(message=message):
                return TextOutput(text=f"ERROR: {message}", red=True)

            case AddInstrumentResponse(
                instrument=instrument,
                price_ticks=price_ticks,
            ):
                return TextOutput(
                    text=(
                        f"Successfully added instrument {instrument.symbol} with "
                        f"{instrument.total_supply} units allocated at "
                        f"{price_ticks} ticks."
                    )
                )

            case AddParticipantResponse(participant=participant):
                return TextOutput(
                    text=f"Successfully added participant {participant.participant_id}"
                )

            case PlaceOrderResponse(order=order):
                return TextOutput(
                    text=f"Successfully placed order with ID {order.order_id}"
                )

            case CancelOrderResponse(order_id=order_id):
                return TextOutput(text=f"Successfully cancelled order {order_id}")

            case SetTimeMultiplierResponse(multiplier=multiplier):
                return TextOutput(text=f"Time multiplier set to {multiplier}")

            case FastForwardResponse(timestamp=timestamp):
                return TextOutput(text=f"Current time: {timestamp}")

            case ListInstrumentsResponse(instruments=instruments):
                table = tabulate(
                    (
                        (instrument.symbol, instrument.total_supply)
                        for instrument in instruments
                    ),
                    headers=("INSTRUMENT", "TOTAL SUPPLY"),
                    tablefmt="simple",
                )
                return TextOutput(text=table)

            case ListParticipantsResponse(participants=participants):
                table = tabulate(
                    (
                        (
                            participant.participant_id,
                            self._format_cash(participant.balance),
                            self._format_cash(participant.net_worth),
                        )
                        for participant in participants
                    ),
                    headers=("PARTICIPANT", "BALANCE", "NET WORTH"),
                    tablefmt="simple",
                    colalign=("left", "right", "right"),
                )
                return TextOutput(text=table)

            case ShowBookResponse(book=book):
                rows = [
                    (
                        "SELL",
                        entry.price_ticks,
                        entry.remaining_quantity,
                        entry.order_id,
                    )
                    for entry in reversed(book.asks)
                ]
                rows.extend(
                    (
                        "BUY",
                        entry.price_ticks,
                        entry.remaining_quantity,
                        entry.order_id,
                    )
                    for entry in book.bids
                )

                table = tabulate(
                    rows,
                    headers=("SIDE", "PRICE", "QTY", "ORDER"),
                    tablefmt="simple",
                    colalign=("left", "right", "right", "right"),
                )
                return TextOutput(text=f"BOOK {book.symbol}\n\n{table}")

            case ShowParticipantResponse(participant=participant):
                cash_table = tabulate(
                    (
                        (
                            self._format_cash(participant.available_cash),
                            self._format_cash(participant.reserved_cash),
                            self._format_cash(participant.total_cash),
                            self._format_gain(participant.unrealised_gain),
                            self._format_cash(participant.net_worth),
                        ),
                    ),
                    headers=(
                        "AVAILABLE CASH",
                        "RESERVED CASH",
                        "TOTAL CASH",
                        "UNREALISED GAIN",
                        "NET WORTH",
                    ),
                    tablefmt="simple",
                    colalign=("right", "right", "right", "right", "right"),
                )
                position_table = tabulate(
                    (
                        (
                            position.symbol,
                            position.available_quantity,
                            position.reserved_quantity,
                            position.total_quantity,
                            (
                                self._format_cash(position.average_cost_ticks)
                                if position.average_cost_ticks is not None
                                else "N/A"
                            ),
                            (
                                self._format_cash(position.mark_price_ticks)
                                if position.mark_price_ticks is not None
                                else "N/A"
                            ),
                        )
                        for position in participant.positions
                    ),
                    headers=(
                        "SYMBOL",
                        "AVAILABLE",
                        "RESERVED",
                        "TOTAL",
                        "AVG COST",
                        "MARK PRICE",
                    ),
                    tablefmt="simple",
                    colalign=("left", "right", "right", "right", "right", "right"),
                )
                return TextOutput(
                    text=(
                        f"PARTICIPANT {participant.participant_id}\n"
                        f"NAME {participant.display_name}\n\n"
                        f"{cash_table}\n\nPOSITIONS\n{position_table}"
                    )
                )

            case ShowPerformanceResponse(history=history):
                return FigureOutput(figure=self._generate_performance_graph(history))

            case ShowTradesResponse(trades=trades):
                rows = [
                    (
                        trade.timestamp,
                        trade.symbol,
                        trade.price_ticks,
                        trade.quantity,
                        trade.buyer_id,
                        trade.seller_id,
                    )
                    for trade in trades
                ]

                table = tabulate(
                    rows,
                    headers=("TIMESTAMP", "SYMBOL", "PRICE", "QTY", "BUYER", "SELLER"),
                    tablefmt="simple",
                    colalign=("left", "right", "right", "right", "right", "right"),
                )
                return TextOutput(text=table)

            case ShowGraphResponse(
                symbol=symbol,
                entries=entries,
                fundamental_entries=fundamental_entries,
                midpoint_entries=midpoint_entries,
            ):
                graph = self._generate_graph(
                    symbol,
                    entries,
                    fundamental_entries,
                    midpoint_entries,
                )
                return FigureOutput(figure=graph)

            case ShowStatsResponse(statistics=statistics):
                rows = (
                    (
                        "Last trade",
                        statistics.last_trade_price_ticks
                        if statistics.last_trade_price_ticks is not None
                        else "N/A",
                    ),
                    (
                        "Book midpoint",
                        statistics.midpoint_ticks
                        if statistics.midpoint_ticks is not None
                        else "N/A",
                    ),
                    (
                        "Bid-ask spread",
                        statistics.spread_ticks
                        if statistics.spread_ticks is not None
                        else "N/A",
                    ),
                    (
                        "Spread",
                        f"{statistics.spread_percent:.4f}%"
                        if statistics.spread_percent is not None
                        else "N/A",
                    ),
                    ("Trade count", statistics.trade_count),
                    ("Traded volume", statistics.traded_volume),
                    (
                        "VWAP",
                        f"{statistics.vwap_ticks:.2f}"
                        if statistics.vwap_ticks is not None
                        else "N/A",
                    ),
                    (
                        "Midpoint volatility",
                        f"{statistics.midpoint_volatility:.4%}"
                        if statistics.midpoint_volatility is not None
                        else "N/A",
                    ),
                )
                table = tabulate(rows, headers=("METRIC", "VALUE"), tablefmt="simple")
                return TextOutput(
                    text=(
                        f"STATS {statistics.symbol}\n"
                        f"WINDOW {statistics.window_start}-{statistics.window_end}\n\n"
                        f"{table}"
                    )
                )

            case ShowTimeResponse(timestamp=timestamp):
                return TextOutput(text=f"Current time: {timestamp}")
