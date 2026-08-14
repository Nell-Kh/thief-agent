"""Tests for the transport behaviours a tunnel - not a LAN - forced on us.

Kept apart from :mod:`test_http_transport` under the 150-line rule, and because
they are a different claim: not "the transport delivers a message" but "the
transport survives, and explains, a connection that misbehaves".
"""

from __future__ import annotations

import asyncio

import pytest

from police_thief.infra.http_transport import McpHttpTransport
from police_thief.infra.transport import TransportError


def test_a_message_less_failure_names_its_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bug that started this: '(Client failed to connect: )' said nothing."""
    transport = McpHttpTransport("https://tunnel.example/mcp")

    class SilentError(Exception):
        """A failure that stringifies to nothing, as a dropped tunnel's does."""

    async def drop(_tool: str, _payload: dict) -> dict:
        """Fail the way a reaped tunnel connection fails: silently."""
        raise SilentError

    monkeypatch.setattr(transport, "_call", drop)
    with pytest.raises(TransportError, match="SilentError"):
        transport.send("receive_turn", {})


def test_the_calling_thread_is_never_wedged_by_a_hung_peer() -> None:
    """A peer that accepts the connection and then says nothing must not hang us."""
    transport = McpHttpTransport("https://tunnel.example/mcp", timeout=0.1)

    async def never_answers(_tool: str, _payload: dict) -> dict:
        """Stand in for a peer that holds the connection open and goes quiet."""
        await asyncio.sleep(3600)

    transport._call = never_answers  # noqa: SLF001 - the point is the send() path
    with pytest.raises(TransportError, match="transport failure"):
        transport.send("receive_turn", {})


def test_closing_a_transport_twice_is_harmless() -> None:
    transport = McpHttpTransport("https://tunnel.example/mcp")
    transport.close()
    transport.close()
