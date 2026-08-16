"""Tests for dialling a role-split opponent: one endpoint per role."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _series_subgame import peer_url_for  # noqa: E402


def test_a_single_endpoint_opponent_is_dialled_at_peer_for_both_roles() -> None:
    args = SimpleNamespace(peer="https://one/mcp", peer_thief="")
    assert peer_url_for(args, "police") == "https://one/mcp"
    assert peer_url_for(args, "thief") == "https://one/mcp"


def test_a_role_split_opponent_is_dialled_at_its_thief_when_we_are_police() -> None:
    """sharNamr, 2026-08-15: two processes, two tunnels, one per role."""
    args = SimpleNamespace(peer="https://their-cop/mcp", peer_thief="https://their-thief/mcp")
    assert peer_url_for(args, "police") == "https://their-thief/mcp"
    assert peer_url_for(args, "thief") == "https://their-cop/mcp"


def test_an_old_args_object_without_the_flag_still_works() -> None:
    args = SimpleNamespace(peer="https://one/mcp")
    assert peer_url_for(args, "police") == "https://one/mcp"


def test_a_mailbox_reply_is_not_a_refusal() -> None:
    from _series_lib import spoken_refusal

    assert spoken_refusal({"ok": True}) == ""
    assert spoken_refusal({"accepted": True, "terms": {}}) == ""
    assert spoken_refusal(None) == ""


def test_a_spoken_no_is_a_refusal_never_a_success() -> None:
    """sharNamr, 2026-08-15: a peer that says no in the reply must be believed."""
    from _series_lib import spoken_refusal

    assert "identity" in spoken_refusal({"accepted": False, "reason": "identity is required"})
    assert spoken_refusal({"ok": False}) == "no reason given"
    assert spoken_refusal({"refused": "SPAR-N08"}) == "SPAR-N08"
    assert spoken_refusal({"error": "terms mismatch"}) == "terms mismatch"


def _box(current_number: int, pending: object | None = None):
    """A SwappableHandler whose active handler refuses everything by sub-game."""
    from _series_lib import SwappableHandler

    from police_thief.services.inbound import HandshakeRejectedError

    class Refusing:
        """A handler that refuses every greeting naming another sub-game."""

        declared_sub_game = current_number

        def negotiate(self, message):
            """Stand in for a handler that refuses every foreign greeting."""
            raise HandshakeRejectedError(
                f"sub-game mismatch: we are playing {current_number}, "
                f"they declare {message.get('sub_game_number')}"
            )

    box = SwappableHandler()
    box.current = Refusing()
    box.pending = pending
    return box


def test_an_early_greeting_is_retryable_not_a_refusal() -> None:
    """najamjad, 2026-08-16: their cop opened sub-game 2 during our sub-game 1.

    Two processes, one per role, both dialling our single door - so the cop
    process greets for its own first game while the thief process is still
    playing ours. Answering that with a permanent refusal ends a series over a
    race that resolves itself in seconds.
    """
    from fastmcp.exceptions import ToolError

    box = _box(1)
    try:
        box.negotiate({"sub_game_number": 2})
    except ToolError as error:
        # ToolError, not a bare exception: FastMCP treats it as expected and
        # client-facing, so the peer still gets a retryable failure but our
        # operator log does not get a stack dump per poll.
        assert "has not started" in str(error)
    else:
        raise AssertionError("an early greeting must be answered, and retryably")


def test_a_greeting_for_a_sealed_sub_game_still_refuses() -> None:
    """Backwards is not a race - that sub-game is reported and cannot be replayed."""
    from police_thief.services.inbound import HandshakeRejectedError

    box = _box(3)
    try:
        box.negotiate({"sub_game_number": 2})
    except HandshakeRejectedError:
        pass
    else:
        raise AssertionError("a greeting for a settled sub-game must refuse")


def test_a_staged_next_sub_game_is_still_promoted_on_the_boundary() -> None:
    class Accepting:
        """The staged next-sub-game handler, which accepts what promoted it."""

        declared_sub_game = 2

        def negotiate(self, message):
            """The staged handler, which accepts the greeting that promoted it."""
            return {"accepted": True}

    box = _box(1, pending=Accepting())
    assert box.negotiate({"sub_game_number": 2}) == {"accepted": True}
    assert box.pending is None


def test_a_stale_pending_never_replaces_a_live_handler() -> None:
    """najamjad, 2026-08-16: sub-game 3's greeting arrived during sub-game 2.

    ``pending`` still held the handler staged for sub-game 2 - never consumed,
    because the opponent arrived late and ``play_sub_game`` built its own. The
    old code promoted whatever was staged, so a dead sub-game-2 handler
    replaced the live one holding that game's turn buffer, and a sub-game being
    played correctly died. Promotion must name the sub-game it answers.
    """
    class Stale:
        """A handler staged for a sub-game that is already being played."""

        declared_sub_game = 2

        def negotiate(self, message):
            """Never reached: this handler must not be promoted."""
            raise AssertionError("a stale pending handler was promoted")

    from fastmcp.exceptions import ToolError

    box = _box(2, pending=Stale())
    try:
        box.negotiate({"sub_game_number": 3})
    except ToolError as error:
        assert "has not started" in str(error)
    else:
        raise AssertionError("an early greeting must be answered retryably")
    assert isinstance(box.pending, Stale), "a non-matching pending must survive untouched"
    assert box.current.declared_sub_game == 2, "the live handler must stay bound"
