from dataclasses import dataclass

from mini_stock_exchange.exchange.exchange import Exchange
from mini_stock_exchange.exchange.models import ParticipantId, Timestamp


@dataclass(kw_only=True)
class LongTermHolderAgent:
    """A passive agent which holds its initial positions without trading."""

    participant_id: ParticipantId

    def act(self, exchange: Exchange, timestamp: Timestamp) -> None:
        """Take no action."""
