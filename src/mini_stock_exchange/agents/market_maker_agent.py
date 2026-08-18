from dataclasses import dataclass

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import ParticipantId, Timestamp
from mini_stock_exchange.simulation import FundamentalValueEstimator


@dataclass(kw_only=True)
class MarketMakerAgent:
    """A trading agent intended to provide continuous two-sided liquidity."""

    participant_id: ParticipantId
    fundamental_value_estimator: FundamentalValueEstimator

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        """Consider updating this market maker's quotes for one simulation step."""
