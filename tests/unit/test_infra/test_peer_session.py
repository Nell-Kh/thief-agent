"""Tests for the held-open peer session: reuse, reconnect, and honest errors."""

from __future__ import annotations

import pytest

from police_thief.infra.async_loop import shared_loop
from police_thief.infra.peer_session import TUNNEL_HEADERS, PeerSession
from police_thief.infra.transport import TransportError


class SilentError(Exception):
    """A message-less failure, exactly as a dropped tunnel raises one."""


class FakeClient:
    """A fastmcp client double: counts sessions and can fail on demand."""

    def __init__(self, opened: list[int], fail_on_call: bool = False,
                 fail_on_open: bool = False) -> None:
        """Record openings into a shared list so a test can count sessions."""
        self._opened = opened
        self._fail_on_call = fail_on_call
        self._fail_on_open = fail_on_open
        self.closed = False

    async def __aenter__(self) -> FakeClient:
        """Open the session, or fail the way an unreachable tunnel does."""
        if self._fail_on_open:
            raise SilentError
        self._opened.append(1)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close the session."""
        self.closed = True

    async def call_tool(self, tool: str, arguments: dict) -> dict:
        """Answer the call, or fail mid-stream."""
        if self._fail_on_call:
            raise SilentError
        return {"tool": tool, "arguments": arguments}


def _session(monkeypatch: pytest.MonkeyPatch, **flags) -> tuple[PeerSession, list[int]]:
    """A session whose every client is a :class:`FakeClient`, plus its open log."""
    opened: list[int] = []
    session = PeerSession("https://tunnel.example/mcp", timeout=1.0)
    monkeypatch.setattr(session, "_build", lambda: FakeClient(opened, **flags))
    return session, opened


def _run(coro):
    """Drive a session coroutine to completion from a synchronous test."""
    return shared_loop().run(coro, timeout=5)


def test_the_ngrok_browser_warning_is_skipped_by_default() -> None:
    """The free tier answers a suspected browser with HTML instead of the peer."""
    assert TUNNEL_HEADERS["ngrok-skip-browser-warning"] == "true"


def test_nothing_is_dialled_until_the_first_call(monkeypatch) -> None:
    session, opened = _session(monkeypatch)
    assert not session.connected
    assert opened == []


def test_one_session_serves_many_calls(monkeypatch) -> None:
    """The change that matters: five moves, one connection - not five."""
    session, opened = _session(monkeypatch)
    for step in range(5):
        _run(session.call("receive_turn", {"message": {"step": step}}))
    assert opened == [1]
    assert session.connected


def test_a_failed_call_discards_the_session(monkeypatch) -> None:
    """A dead session must not be handed to the retry that follows it."""
    session, _opened = _session(monkeypatch, fail_on_call=True)
    with pytest.raises(TransportError):
        _run(session.call("receive_turn", {"message": {}}))
    assert not session.connected


def test_the_retry_after_a_drop_gets_a_fresh_connection(monkeypatch) -> None:
    opened: list[int] = []
    session = PeerSession("https://tunnel.example/mcp", timeout=1.0)
    failing = [True, False]
    monkeypatch.setattr(
        session, "_build", lambda: FakeClient(opened, fail_on_call=failing.pop(0))
    )
    with pytest.raises(TransportError):
        _run(session.call("receive_turn", {"message": {}}))
    assert _run(session.call("receive_turn", {"message": {}}))["tool"] == "receive_turn"
    assert opened == [1, 1]


def test_a_message_less_failure_still_names_its_type(monkeypatch) -> None:
    """The whole point of the change: no more '(Client failed to connect: )'."""
    session, _opened = _session(monkeypatch, fail_on_call=True)
    with pytest.raises(TransportError, match="SilentError"):
        _run(session.call("receive_turn", {"message": {}}))


def test_a_failure_to_open_names_the_url_and_the_type(monkeypatch) -> None:
    session, _opened = _session(monkeypatch, fail_on_open=True)
    with pytest.raises(TransportError, match="could not open a session"):
        _run(session.connect())
    assert not session.connected


def test_closing_an_unopened_session_is_harmless(monkeypatch) -> None:
    session, _opened = _session(monkeypatch)
    _run(session.aclose())
    assert not session.connected
