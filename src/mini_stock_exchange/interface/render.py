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
    GraphEntry,
    PlaceOrderResponse,
    ShowBookResponse,
    ShowGraphResponse,
    ShowTimeResponse,
    ShowTradesResponse,
)
from mini_stock_exchange.exchange.models import Symbol

type RenderedOutput = TextOutput | FigureOutput


@dataclass(frozen=True, kw_only=True)
class TextOutput:
    text: str
    red: bool = False


@dataclass(frozen=True, kw_only=True)
class FigureOutput:
    figure: Figure


class Renderer:
    @staticmethod
    def _generate_graph(symbol: Symbol, entries: tuple[GraphEntry, ...]) -> Figure:
        figure, axes = plt.subplots(figsize=(8, 4.5), layout="constrained")

        axes.set_title(f"{symbol} trade price history")
        axes.set_xlabel("Simulation time")
        axes.set_ylabel("Price (ticks)")
        axes.grid(axis="both", alpha=0.3)

        if entries:
            axes.plot(
                [entry.timestamp for entry in entries],
                [entry.price_ticks for entry in entries],
                marker="o",
            )
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

            case AddInstrumentResponse(instrument=instrument):
                return TextOutput(
                    text=f"Successfully added instrument {instrument.symbol}."
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

            case ShowGraphResponse(symbol=symbol, entries=entries):
                graph = self._generate_graph(symbol, entries)
                return FigureOutput(figure=graph)

            case ShowTimeResponse(timestamp=timestamp):
                return TextOutput(text=f"Current time: {timestamp}")
