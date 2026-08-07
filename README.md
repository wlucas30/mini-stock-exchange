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
places an initial sell order for 100 units of each instrument on behalf of the
`EXCHANGE_MASTER` participant. Prices in the configuration file are integer
ticks, where one tick is one cent.
