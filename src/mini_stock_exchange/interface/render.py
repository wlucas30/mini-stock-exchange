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
    ShowTimeResponse,
    ShowTradesResponse,
)
from mini_stock_exchange.exchange.models import Cash, Symbol

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
                marker="o",
                label="Trade price",
            )

        if fundamental_entries:
            axes.plot(
                [entry.timestamp for entry in fundamental_entries],
                [entry.price_ticks for entry in fundamental_entries],
                label="Fundamental value",
            )

        if entries or fundamental_entries:
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

    def render(self, response: ExecutorResponse) -> RenderedOutput:
        match response:
            case ErrorResponse(message=message):
                return TextOutput(text=f"ERROR: {message}", red=True)

            case AddInstrumentResponse(
                instrument=instrument,
                price_ticks=price_ticks,
                volume=volume,
            ):
                return TextOutput(
                    text=(
                        f"Successfully added instrument {instrument.symbol} with "
                        f"{volume} units allocated at {price_ticks} ticks."
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

            case ListInstrumentsResponse(symbols=symbols):
                table = tabulate(
                    ((symbol,) for symbol in symbols),
                    headers=("INSTRUMENT",),
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
            ):
                graph = self._generate_graph(symbol, entries, fundamental_entries)
                return FigureOutput(figure=graph)

            case ShowTimeResponse(timestamp=timestamp):
                return TextOutput(text=f"Current time: {timestamp}")
