"""Tests for series fault containment - a bad sub-game must not zero the series."""

from __future__ import annotations

import pytest

from police_thief.infra.mcp_client import PeerUnreachableError
from police_thief.infra.transport import TransportError
from police_thief.services.deadline import DeadlineExpiredError
from police_thief.services.series_guard import (
    CONTAINED_FAILURES,
    failure_reason,
    technical_loss_row,
)
from police_thief.services.turn_reorder import HandshakeRejectedError


@pytest.mark.parametrize(
    "error",
    [
        PeerUnreachableError("opponent silent"),
        TransportError("connection reset"),
        HandshakeRejectedError("equivocated commit"),
        TimeoutError("no turn arrived"),
        DeadlineExpiredError("reply too late"),  # a TimeoutError subclass
    ],
)
def test_every_live_failure_is_contained(error: Exception) -> None:
    """The exact exceptions a flaky tunnel throws are all caught by the tuple."""
    try:
        raise error
    except CONTAINED_FAILURES as caught:
        assert caught is error
    else:  # pragma: no cover - the raise above always fires
        pytest.fail(f"{type(error).__name__} escaped containment")


def test_a_programming_bug_is_not_swallowed() -> None:
    """Containment is for network faults, not for masking our own KeyError."""
    with pytest.raises(KeyError):
        try:
            raise KeyError("a real bug")
        except CONTAINED_FAILURES:  # pragma: no cover - must not catch
            pytest.fail("containment swallowed a programming error")


def test_the_technical_loss_row_is_shaped_like_a_played_row() -> None:
    row = technical_loss_row(
        sub_game_number=3, us="yanell11", opponent="rivals", role="police",
        expect_role="thief", game_id="yanell11-vs-rivals", github_commit="abc123",
        reason="PeerUnreachableError: opponent silent",
    )
    assert row["result"] == "technical_loss"
    assert row["score"] == {"yanell11": 0, "rivals": 0}  # nobody scores
    assert row["winner_group"] is None and row["tie"] is False
    assert row["roles"] == {"yanell11": "police", "rivals": "thief"}  # complementary
    assert row["github_commit"] == {"yanell11": "abc123", "rivals": "unknown"}
    # EMPTY, not a plausible name. A sub-game that never played writes no log,
    # and a report that names one sends an auditor to a file that does not
    # exist - which reads like withheld evidence rather than a network failure.
    # Three rows of our own filed najamjad series did exactly that.
    assert row["log_files"] == {}
    assert row["audit"] == {"log_verified": False, "tampered": False,
                            "reason": "PeerUnreachableError: opponent silent"}


def test_a_contained_failure_is_never_scored_as_tampering() -> None:
    """A silent opponent is a technical loss, not a forgery - keep them distinct."""
    row = technical_loss_row(
        sub_game_number=1, us="a", opponent="b", role="thief", expect_role="police",
        game_id="a-vs-b", github_commit="x", reason="timeout",
    )
    assert row["audit"]["tampered"] is False  # not a tamper_forfeit


def test_failure_reason_is_a_compact_type_and_message() -> None:
    assert failure_reason(PeerUnreachableError("gone")) == "PeerUnreachableError: gone"


# --- crash recovery: played games must outlive the process -------------------


def test_rows_survive_a_process_that_never_reaches_the_end(tmp_path) -> None:
    """The whole point: five real sub-games must not die with the interpreter."""
    from police_thief.services.series_guard import load_rows, save_rows

    played = [{"sub_game_number": n, "score": {"us": 20, "them": 5}} for n in range(1, 6)]
    save_rows(tmp_path / "series", played)
    assert load_rows(tmp_path / "series") == played  # a fresh process reads them back


def test_the_checkpoint_is_replaced_atomically(tmp_path) -> None:
    """Each save must leave one whole file, never a truncated one."""
    from police_thief.services.series_guard import load_rows, save_rows

    save_rows(tmp_path / "s", [{"sub_game_number": 1}])
    save_rows(tmp_path / "s", [{"sub_game_number": 1}, {"sub_game_number": 2}])
    assert len(load_rows(tmp_path / "s")) == 2
    leftovers = list((tmp_path / "s").glob("*.tmp"))
    assert leftovers == []  # no scratch file left behind


def test_a_corrupt_checkpoint_never_blocks_a_new_series(tmp_path) -> None:
    """Recovery is a bonus path - it must not be what stops us from playing."""
    from police_thief.services.series_guard import checkpoint_path, load_rows

    path = checkpoint_path(tmp_path / "s")
    path.parent.mkdir(parents=True)
    path.write_text("{ this is not json", encoding="utf-8")
    assert load_rows(tmp_path / "s") == []


def test_no_checkpoint_is_simply_an_empty_recovery(tmp_path) -> None:
    from police_thief.services.series_guard import load_rows

    assert load_rows(tmp_path / "never-run") == []


def test_a_previous_run_is_archived_not_destroyed(tmp_path) -> None:
    """Re-running after a crash must not delete the only record of real games."""
    from police_thief.services.series_guard import archive_previous_run, save_rows

    series = tmp_path / "friendly_a-vs-b"
    save_rows(series, [{"sub_game_number": 1}])
    archive = archive_previous_run(series)
    assert archive is not None and archive.exists()
    assert not series.exists()  # moved aside, ready for a clean run
    assert "superseded" in archive.name


def test_repeated_reruns_keep_every_archive(tmp_path) -> None:
    """A second crash must not overwrite the first crash's evidence."""
    from police_thief.services.series_guard import archive_previous_run, save_rows

    series = tmp_path / "friendly_a-vs-b"
    archives = []
    for attempt in range(3):
        save_rows(series, [{"sub_game_number": attempt}])
        archives.append(archive_previous_run(series))
    assert len({str(a) for a in archives}) == 3  # three distinct, all preserved
    assert all(a.exists() for a in archives)


def test_archiving_an_untouched_directory_is_a_no_op(tmp_path) -> None:
    from police_thief.services.series_guard import archive_previous_run

    assert archive_previous_run(tmp_path / "absent") is None
    (tmp_path / "empty").mkdir()
    assert archive_previous_run(tmp_path / "empty") is None  # nothing worth keeping
