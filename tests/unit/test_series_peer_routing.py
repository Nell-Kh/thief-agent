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


class _Clock:
    """A monotonic clock the test drives, so patience costs no wall time."""

    def __init__(self) -> None:
        """Start at zero; only :meth:`sleep` ever moves it."""
        self.now = 0.0

    def __call__(self) -> float:
        """Read the clock, in the shape ``negotiate_patiently`` expects."""
        return self.now

    def sleep(self, seconds: float) -> None:
        """Spend the pause instantly, so a 120s budget costs no wall time."""
        self.now += seconds


class _Peer:
    """A peer that answers ``script[i]`` to the i-th greeting, last reply sticking."""

    def __init__(self, *script: object) -> None:
        """Queue the replies; an ``Exception`` in the script is raised, not returned."""
        self.script = list(script)
        self.calls = 0

    def negotiate(self, _greeting: dict) -> object:
        """Answer the next scripted reply, repeating the last one forever."""
        self.calls += 1
        reply = self.script[min(self.calls - 1, len(self.script) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_a_reasonless_no_is_re_offered_until_the_peer_is_ready() -> None:
    """najamjad, 2026-08-16: sub-games 4, 5 and 6, each lost in 0.00 seconds.

    They run one process per role against our single door, so dialling them for
    sub-game n while their other role is mid-sub-game gets a bare
    ``{"ok": false}``. We answer THEIR early greeting with "not started yet -
    retry when it does" and expect patience; quitting on the first bare no was
    the same race, refused in the opposite direction, and it cost three games
    out of six with 120 seconds of budget unspent.
    """
    from _series_lib import negotiate_patiently

    clock = _Clock()
    peer = _Peer({"ok": False}, {"ok": False}, {"ok": False}, {"ok": True, "terms": {}})
    said: list[str] = []

    reply = negotiate_patiently(peer, {"sub_game_number": 4}, wait_seconds=120,
                                clock=clock, announce=said.append, sleep=clock.sleep)

    assert reply == {"ok": True, "terms": {}}
    assert peer.calls == 4, "the bare no must be re-offered, not believed once"
    assert clock.now <= 120, "recovery must happen inside the opening budget"
    assert any("not yet" in note for note in said), "the operator must be told why we wait"


def test_a_refusal_that_names_a_reason_still_fails_on_the_first_call() -> None:
    """The other half: sharNamr's lesson must survive najamjad's fix.

    A digest or identity mismatch is not a race and never resolves itself, so
    re-offering it would only spend the budget before failing anyway.
    """
    import pytest
    from _series_lib import HandshakeRejectedError, negotiate_patiently

    clock = _Clock()
    peer = _Peer({"accepted": False, "reason": "contract digest mismatch"})

    with pytest.raises(HandshakeRejectedError, match="contract digest mismatch"):
        negotiate_patiently(peer, {}, wait_seconds=120, clock=clock,
                            announce=lambda _note: None, sleep=clock.sleep)

    assert peer.calls == 1, "a stated refusal must not be re-offered"
    assert clock.now == 0.0, "and must not spend the patience budget"


def test_a_peer_that_only_ever_says_no_becomes_a_technical_loss_at_the_deadline() -> None:
    """Patience is a ceiling on waiting, not a way to avoid the verdict."""
    import pytest
    from _series_lib import HandshakeRejectedError, negotiate_patiently

    clock = _Clock()
    peer = _Peer({"ok": False})

    with pytest.raises(HandshakeRejectedError, match="no reason given"):
        negotiate_patiently(peer, {}, wait_seconds=10, clock=clock,
                            announce=lambda _note: None, sleep=clock.sleep)

    assert clock.now >= 10, "the whole budget must be spent before giving up"
    assert peer.calls > 1, "and it must have been re-offered while spending it"


def test_the_silence_branch_paces_itself_instead_of_spinning() -> None:
    """It used to ``continue`` with no pause, paced only by PeerClient's backoff.

    Measured against an instant-failing stub: 7.2 million calls in 3 seconds.
    Nothing was broken while the transport happened to be slow, which is the
    kind of load-bearing accident worth removing.
    """
    from _series_lib import REOFFER_PAUSE_SECONDS, negotiate_patiently

    from police_thief.infra.mcp_client import PeerUnreachableError

    clock = _Clock()
    peer = _Peer(PeerUnreachableError("down"), PeerUnreachableError("down"), {"ok": True})

    negotiate_patiently(peer, {}, wait_seconds=120, clock=clock,
                        announce=lambda _note: None, sleep=clock.sleep)

    assert peer.calls == 3
    assert clock.now == 2 * REOFFER_PAUSE_SECONDS, "each retry must cost a real pause"
