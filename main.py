# pyright: reportUnknownMemberType=false

from pathlib import Path
from time import time_ns

from matplotlib import pyplot as plt

from mini_stock_exchange.configuration import seed_exchange
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.interface.controller import Controller
from mini_stock_exchange.interface.render import FigureOutput, TextOutput

RED = "\033[31m"
RESET = "\033[0m"
DEFAULT_INSTRUMENTS = Path(__file__).parent / "config" / "default_instruments.csv"


def display(output: TextOutput | FigureOutput) -> None:
    match output:
        case TextOutput(text=text, red=True):
            print(f"{RED}{text}{RESET}")

        case TextOutput(text=text):
            print(text)

        case FigureOutput(figure=figure):
            figure.show()
            plt.show(block=False)


def main() -> None:
    exchange = Exchange(time=time_ns)
    seed_exchange(exchange, DEFAULT_INSTRUMENTS)
    controller = Controller(exchange)

    print("Mini Stock Exchange")
    print("Enter a command, or press Ctrl-D to exit.")

    while True:
        try:
            source = input("> ")
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not source.strip():
            continue

        display(controller.process(source))


if __name__ == "__main__":
    main()
