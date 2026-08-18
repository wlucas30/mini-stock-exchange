# pyright: reportUnknownMemberType=false

from pathlib import Path

from matplotlib import pyplot as plt

from mini_stock_exchange.configuration import seed_agents, seed_exchange
from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.interface.controller import Controller
from mini_stock_exchange.interface.render import FigureOutput, TextOutput
from mini_stock_exchange.simulation import Simulation, SimulationTime

RED = "\033[31m"
RESET = "\033[0m"
DEFAULT_INSTRUMENTS = Path(__file__).parent / "config" / "default_instruments.csv"
DEFAULT_AGENTS = Path(__file__).parent / "config" / "default_agents.csv"


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
    simulation_time = SimulationTime()
    exchange = Exchange(time=lambda: simulation_time.current_time)
    market_states = seed_exchange(exchange, DEFAULT_INSTRUMENTS)
    agents = seed_agents(
        exchange,
        DEFAULT_AGENTS,
        lambda symbol: next(
            market_state.fundamental_value_estimate
            for market_state in market_states
            if market_state.symbol == symbol
        ),
    )
    simulation = Simulation(
        exchange,
        simulation_time,
        agents=agents,
        market_states=market_states,
    )
    controller = Controller(simulation)

    print("Mini Stock Exchange")
    print("Enter a command, or press Ctrl-D to exit.")

    try:
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
    finally:
        controller.close()


if __name__ == "__main__":
    main()
