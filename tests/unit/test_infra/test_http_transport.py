"""Tests for the HTTP transport, all network mocked."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from police_thief.infra.http_transport import McpHttpTransport, _extract_reply
from police_thief.infra.transport import TransportError


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


class _FakeMcpClient:
    """A fastmcp.Client double that counts sessions instead of dialing out."""

    sessions_opened = 0
    sessions_closed = 0
    calls: list[str] = []
    fail_next = 0

    def __init__(self, _url: str) -> None:
        """Accept the URL like the real client, remembering nothing."""

    async def __aenter__(self) -> _FakeMcpClient:
        """Open a counted session."""
        type(self).sessions_opened += 1
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Close a counted session."""
        type(self).sessions_closed += 1

    async def call_tool(self, tool: str, _args: dict) -> SimpleNamespace:
        """Answer like a healthy peer, unless a failure was scheduled."""
        if type(self).fail_next > 0:
            type(self).fail_next -= 1
            raise RuntimeError("connection reset")
        type(self).calls.append(tool)
        return SimpleNamespace(data={"accepted": True}, structured_content=None)

    @classmethod
    def reset(cls) -> None:
        """Zero the counters between tests."""
        cls.sessions_opened = cls.sessions_closed = cls.fail_next = 0
        cls.calls = []


@pytest.fixture
def fake_session(monkeypatch: pytest.MonkeyPatch) -> type[_FakeMcpClient]:
    """Install the counting double where the transport imports fastmcp.Client."""
    _FakeMcpClient.reset()
    monkeypatch.setattr("fastmcp.Client", _FakeMcpClient)
    return _FakeMcpClient


def test_one_session_serves_many_calls(fake_session: type[_FakeMcpClient]) -> None:
    """The ngrok lesson: per-call sessions blew the free tier's request cap."""
    transport = McpHttpTransport("http://127.0.0.1:9/mcp")
    for _ in range(3):
        assert transport.send("receive_turn", {})["accepted"]
    transport.close()
    assert fake_session.sessions_opened == 1
    assert fake_session.calls == ["receive_turn"] * 3
    assert fake_session.sessions_closed == 1


def test_a_failed_call_drops_the_session_and_the_next_call_reconnects(
    fake_session: type[_FakeMcpClient],
) -> None:
    transport = McpHttpTransport("http://127.0.0.1:9/mcp")
    fake_session.fail_next = 1
    with pytest.raises(TransportError, match="call to"):
        transport.send("receive_turn", {})
    assert transport.send("receive_turn", {})["accepted"]
    transport.close()
    assert fake_session.sessions_opened == 2, "the broken session must not be reused"


def test_close_before_any_call_is_a_no_op(fake_session: type[_FakeMcpClient]) -> None:
    transport = McpHttpTransport("http://127.0.0.1:9/mcp")
    transport.close()
    assert fake_session.sessions_opened == 0


def test_extract_prefers_structured_data() -> None:
    result = SimpleNamespace(data={"accepted": True}, structured_content=None)
    assert _extract_reply(result) == {"accepted": True}


def test_extract_falls_back_to_structured_content() -> None:
    result = SimpleNamespace(data=None, structured_content={"result": {"accepted": True}})
    assert _extract_reply(result) == {"accepted": True}


def test_an_unreadable_reply_is_an_error() -> None:
    with pytest.raises(TransportError, match="unreadable reply"):
        _extract_reply(SimpleNamespace(data=None, structured_content=None))
