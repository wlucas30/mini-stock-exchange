# mini-stock-exchange

A mini simulated stock exchange written in Python supporting limit orders, cancellations, price-time priority matching and partial fills.

## Setup

Python 3.14 is required.

Create and activate a virtual environment:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

Install the project and its development dependencies:

```bash
python -m pip install -e '.[dev]'
```

Run the tests and code-quality checks:

```bash
pytest
ruff check .
ruff format --check .
```

## Running

Start the interactive exchange with:

```bash
python main.py
```

At startup, `config/default_instruments.csv` creates ALPHA, BETA and GAMMA and
defines each instrument's starting price and total supply. Prices are integer
ticks, where one tick is one cent.

`config/default_agents.csv` creates the simulation's automated traders and
gives each one its configured starting cash balance and strategy. The default
configuration starts eight `RandomNoise` traders with $10,000 each, two
`Fundamental` traders with $20,000 each, and two `MarketMaker` agents with
$20,000 each.

`config/default_agent_positions.csv` allocates the complete initial supply of
each instrument directly to participants. The default configuration divides
each instrument equally between the two market makers and records the starting
price as their acquisition cost.

Simulation time starts at zero and advances once per real second. Use
`SET TIME MULTIPLIER <n>` to change its speed (`0` pauses it) and
`FAST FORWARD <delta>` to advance it immediately. Every intermediate
simulation step is processed so agents can act at each time unit.

Each instrument also has hidden simulation state. Its initial fundamental
value is its issue price, its initial sentiment is neutral, and its initial
volatility is 0.1%. Each simulation step may change sentiment, varies
volatility, and applies a sentiment-biased random movement to fundamental value.
