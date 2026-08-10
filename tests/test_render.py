from mini_stock_exchange.commands.execute import (
    ListParticipantsResponse,
    ShowParticipantResponse,
)
from mini_stock_exchange.exchange.models import (
    ParticipantDetails,
    ParticipantPositionSummary,
    ParticipantSummary,
)
from mini_stock_exchange.interface.render import Renderer, TextOutput


def test_render_participant_list_includes_formatted_balances() -> None:
    response = ListParticipantsResponse(
        participants=(
            ParticipantSummary(participant_id="ALICE", balance=1_000_00),
            ParticipantSummary(participant_id="BOB", balance=25_50),
        )
    )

    output = Renderer().render(response)

    assert isinstance(output, TextOutput)
    assert "PARTICIPANT" in output.text
    assert "BALANCE" in output.text
    assert "ALICE" in output.text
    assert "$1,000.00" in output.text
    assert "BOB" in output.text
    assert "$25.50" in output.text
