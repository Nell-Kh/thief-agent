"""A promoted handler must not swallow the previous sub-game's audit.

The boundary race has two halves and we had only fixed one. Staging the next
sub-game's handler lets a fast opponent's GREETING be answered - but the
sub-game that just ended is still owed one message, the opponent's audit
disclosure, and that message is addressed to the handler promotion just
displaced.

nis-yar1 (2026-08-17) run one fixed-role process per role against our single
door. In sub-game 1 we captured at step 4, sent our disclosure, and got
``{'ok': True}``. Their COP process then greeted sub-game 2, which promoted our
handler; their THIEF's audit for sub-game 1 arrived a moment later and hit the
new handler, which refused it - correctly for sub-game 2 - with "expected an
audit from 'police'". The evidence was delivered and thrown away, and a
sub-game we had already won died waiting for it. Every sub-game after would
have failed the same way.

So the displaced handler stays reachable for exactly as long as it takes the
old sub-game to finish. Nothing is loosened: both handlers still enforce role
and shape, so a genuinely wrong message is refused by both.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _series_lib import SwappableHandler  # noqa: E402

from police_thief.domain.negotiation import build_terms  # noqa: E402
from police_thief.services.inbound import InboundHandler  # noqa: E402
from police_thief.services.turn_reorder import HandshakeRejectedError  # noqa: E402
from police_thief.shared.config import ConfigManager  # noqa: E402
from police_thief.shared.interop import negotiate_extras, terms_from_contract  # noqa: E402


def handler_for(role: str, sub_game: int) -> InboundHandler:
    """An inbound handler as the driver builds one: our role, their role, this sub-game."""
    config = ConfigManager.load(role)
    return InboundHandler(
        our_terms=terms_from_contract(config.contract),
        our_extras=negotiate_extras(role, sub_game, config.interop),
        expect_role="thief" if role == "police" else "police",
        reorder_window=4,
    )


def greeting(role: str, sub_game: int) -> dict:
    """The opponent's handshake payload for ``sub_game``, sent as ``role``."""
    return build_terms(ConfigManager.load(role), peer_id="them", games_played=0,
                       sub_game=sub_game, step0_commit="0" * 64)


def disclosure(sender: str) -> dict:
    """A minimally-shaped audit payload from ``sender``."""
    return {"sender": sender, "records": [], "game_id": "x", "sub_game_number": 1}


@pytest.fixture()
def promoted() -> SwappableHandler:
    """A box that has just been promoted from sub-game 1 (police) to 2 (thief)."""
    box = SwappableHandler()
    box.current = handler_for("police", 1)
    box.pending = handler_for("thief", 2)
    box.negotiate(greeting("police", 2))  # their cop greets sub-game 2 -> promotion
    return box


def test_the_promotion_happened_and_kept_the_displaced_handler(promoted) -> None:
    """Sanity: current moved to sub-game 2 and the old handler was not discarded."""
    assert promoted.current.declared_sub_game == 2
    assert promoted.previous is not None
    assert promoted.previous.declared_sub_game == 1


def test_the_previous_sub_games_audit_still_lands(promoted) -> None:
    """The exact nis-yar1 failure: their thief's audit for sub-game 1, after promotion."""
    promoted.submit_audit(disclosure("thief"))
    assert promoted.previous.audit is not None, "sub-game 1's audit was thrown away"
    assert promoted.current.audit is None, "it must not be filed against sub-game 2"


def test_the_new_sub_games_audit_still_lands_on_the_new_handler(promoted) -> None:
    """The fallback must not steal messages that belong to the live sub-game."""
    promoted.submit_audit(disclosure("police"))
    assert promoted.current.audit is not None
    assert promoted.previous.audit is None


def test_a_genuinely_wrong_sender_is_still_refused_by_both(promoted) -> None:
    """Nothing is accepted loosely - an audit from nobody's role fails on both."""
    with pytest.raises(HandshakeRejectedError):
        promoted.submit_audit(disclosure("referee"))


def test_with_no_promotion_yet_the_active_handler_still_governs() -> None:
    """No displaced handler, no fallback: the original refusal must survive."""
    box = SwappableHandler()
    box.current = handler_for("police", 1)
    with pytest.raises(HandshakeRejectedError):
        box.submit_audit(disclosure("police"))
