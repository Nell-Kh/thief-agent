"""Tests for the HTTP transport and the peer boot, all network mocked."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from police_thief.infra.http_transport import McpHttpTransport, _extract_reply
from police_thief.infra.mcp_client import PeerUnreachableError
from police_thief.infra.transport import TransportError
from police_thief.services import peer_boot
from police_thief.services.peer_boot import BootReport, build_peer, check_connectivity
from police_thief.shared.config import ConfigManager


def test_a_non_http_url_is_rejected() -> None:
    with pytest.raises(TransportError, match="must be http"):
        McpHttpTransport("ftp://somewhere/mcp")


def test_the_url_is_exposed() -> None:
    transport = McpHttpTransport("https://tunnel.example/mcp")
    assert transport.url == "https://tunnel.example/mcp"


def test_send_returns_the_reply_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    transport = McpHttpTransport("http://127.0.0.1:9/mcp")

    async def fake_call(_tool: str, _payload: dict) -> dict:
        """Accept any call, standing in for a healthy peer."""
        return {"accepted": True}

    monkeypatch.setattr(transport, "_call", fake_call)
    assert transport.send("handshake", {})["accepted"]


def test_an_unexpected_failure_becomes_a_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = McpHttpTransport("http://127.0.0.1:9/mcp")

    async def explode(_tool: str, _payload: dict) -> dict:
        """Fail loudly, so the caller's error handling is the thing under test."""
        raise RuntimeError("connection reset")

    monkeypatch.setattr(transport, "_call", explode)
    with pytest.raises(TransportError, match="transport failure"):
        transport.send("commit", {})


def test_extract_prefers_structured_data() -> None:
    result = SimpleNamespace(data={"accepted": True}, structured_content=None)
    assert _extract_reply(result) == {"accepted": True}


def test_extract_falls_back_to_structured_content() -> None:
    result = SimpleNamespace(data=None, structured_content={"result": {"accepted": True}})
    assert _extract_reply(result) == {"accepted": True}


def test_an_unreadable_reply_is_an_error() -> None:
    with pytest.raises(TransportError, match="unreadable reply"):
        _extract_reply(SimpleNamespace(data=None, structured_content=None))


def test_build_peer_wires_the_configured_opponent_url(config_dir) -> None:
    orchestrator = build_peer(ConfigManager.load("police", config_dir))
    assert orchestrator.role == "police"


def _fake_peer(start_match, **inbound) -> SimpleNamespace:
    """An orchestrator double exposing just what the boot touches."""
    inbound.setdefault("opponent_games_played", None)
    inbound.setdefault("opponent_terms", None)
    return SimpleNamespace(
        start_match=start_match,
        fail=lambda _reason: None,
        inbound=SimpleNamespace(**inbound),
    )


def _install(monkeypatch: pytest.MonkeyPatch, fake: SimpleNamespace) -> None:
    """Point the boot at a doubled peer and stub the server thread away."""
    monkeypatch.setattr(peer_boot, "build_peer", lambda _config: fake)
    monkeypatch.setattr(peer_boot, "start_server", lambda *_a, **_k: None)


def test_check_connectivity_reports_a_successful_handshake(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    fake = _fake_peer(lambda **_kw: {"accepted": True}, opponent_games_played=4)
    _install(monkeypatch, fake)
    report = check_connectivity(ConfigManager.load("police", config_dir), "team-a", 1,
                                linger_seconds=0)
    assert isinstance(report, BootReport)
    assert report.handshake_ok
    assert "opponent declared 4 games" in report.detail
    assert report.my_port == 8801


def test_check_connectivity_reports_a_clean_technical_loss(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    """An unreachable opponent must produce a report, never a hang or a crash."""

    def never_answers(**_kw):
        """Stand in for a peer that never replies."""
        raise PeerUnreachableError("negotiate: opponent unreachable after 3 attempts")

    _install(monkeypatch, _fake_peer(never_answers))
    report = check_connectivity(ConfigManager.load("police", config_dir), "team-a", 0,
                                wait_seconds=0)
    assert not report.handshake_ok
    assert "technical loss" in report.detail


def test_check_connectivity_reports_a_contract_rejection(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    """A digest mismatch is a refusal to play, reported as such - never retried."""
    calls = []

    def refuse(**_kw):
        """Refuse with a contract mismatch, which must never be retried."""
        calls.append(1)
        raise RuntimeError("contract mismatch: ours abc, theirs def")

    _install(monkeypatch, _fake_peer(refuse))
    report = check_connectivity(ConfigManager.load("thief", config_dir), "team-b", 0,
                                wait_seconds=60)
    assert not report.handshake_ok
    assert "contract mismatch" in report.detail
    assert calls == [1], "a refusal is an answer; retrying it would waste the window"


def test_the_peer_that_starts_first_waits_instead_of_giving_up(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    """The two-terminal race: whichever peer boots first must wait, not fail.

    Before the rendezvous existed, the first-started peer burned PeerClient's
    short retry budget against a port nobody was listening on yet, reported
    "opponent unreachable", and exited - so `peer --role thief` then
    `peer --role police` could never both succeed.
    """
    attempts = []

    def up_on_the_fourth_try(**_kw):
        """Fail three times, then answer - the opponent starting late."""
        attempts.append(1)
        if len(attempts) < 4:
            raise PeerUnreachableError("opponent unreachable after 3 attempts")
        return {"accepted": True}

    _install(monkeypatch, _fake_peer(up_on_the_fourth_try))
    said = []
    report = check_connectivity(ConfigManager.load("thief", config_dir), "team-a", 0,
                                wait_seconds=60, linger_seconds=0, announce=said.append)
    assert report.handshake_ok
    assert len(attempts) == 4
    assert any("waiting" in message for message in said)


def test_the_rendezvous_window_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    """Waiting must never become hanging: an expired window still reports."""
    clock = iter([0.0, 5.0, 10.0, 99.0, 99.0, 99.0])

    def never_answers(**_kw):
        """Stand in for a peer that never replies."""
        raise PeerUnreachableError("unreachable")

    fake = _fake_peer(never_answers)
    _install(monkeypatch, fake)
    reply, refusal = peer_boot.rendezvous(fake, "team-a", 0, wait_seconds=30,
                                          clock=lambda: next(clock))
    assert reply is None and refusal is None


def test_a_one_sided_handshake_names_the_likely_cause(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    """Heard from them but cannot reach them back: point at opponent_url."""

    def never_answers(**_kw):
        """Stand in for a peer that never replies."""
        raise PeerUnreachableError("unreachable")

    fake = _fake_peer(never_answers, opponent_terms={"group_id": "them"})
    _install(monkeypatch, fake)
    report = check_connectivity(ConfigManager.load("police", config_dir), "team-a", 0,
                                wait_seconds=0)
    assert not report.handshake_ok
    assert "opponent_url" in report.detail


def test_the_winner_of_the_race_lingers_so_the_other_side_can_finish(
    monkeypatch: pytest.MonkeyPatch, config_dir
) -> None:
    """Exiting the instant our own handshake lands would strand the slower peer."""
    _install(monkeypatch, _fake_peer(lambda **_kw: {"accepted": True}))
    slept: list[float] = []
    report = check_connectivity(ConfigManager.load("police", config_dir), "team-a", 0,
                                linger_seconds=12, sleep=slept.append)
    assert report.handshake_ok
    assert slept == [12]

