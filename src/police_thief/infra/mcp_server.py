"""Inbound side over MCP: the tools this peer exposes to its opponent.

Every peer is simultaneously a server and a client - that symmetry is the whole
point of the peer-to-peer design, and MCP is the project's required standard.
The tool set follows the reference implementation (ADR-7): ``negotiate``,
``receive_turn``, ``submit_audit`` and ``receive_control``. One asymmetry is
load-bearing (interop kit, verified against the reference): ``submit_audit``
takes ``payload`` while the other three take ``message`` - a peer that sends
the wrong keyword gets a schema fault, not a game. This module stays a thin
adapter over the :class:`InboundHandler`, which holds all the logic.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from . import wire_trace
from ..services.inbound import InboundHandler

#: The tool names a peer exposes; the client calls these by name.
TOOL_NAMES = ("negotiate", "receive_turn", "submit_audit", "receive_control")


def build_server(handler: InboundHandler, name: str = "police_thief_peer") -> Any:
    """Create a FastMCP server exposing this peer's tools.

    Raises:
        RuntimeError: if the ``fastmcp`` package is unavailable.
    """
    try:
        from fastmcp import FastMCP
    except ImportError as error:  # pragma: no cover - dependency is declared
        raise RuntimeError("fastmcp is required to expose a peer server") from error

    mcp = FastMCP(name)

    def _inbound(tool: str, message: Any, call: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        """Run one inbound tool, recording it to the wire trace either way.

        Opt-in (``PT_WIRE_TRACE``); a no-op otherwise. Records the tool, the
        sub-game this handler is bound to, and - for a turn - the step/sender we
        were handed, so a stall after negotiation can be read off disk as "their
        step-1 turn never arrived" vs "arrived and we rejected it", instead of
        guessed. The exception is re-raised unchanged: tracing only observes.
        """
        sub_game = getattr(handler, "declared_sub_game", None)
        step = message.get("step") if isinstance(message, dict) else None
        # A turn carries ``sender``; a greeting carries ``role`` - trace whichever.
        sender = None
        if isinstance(message, dict):
            sender = message.get("sender", message.get("role"))
        wire_trace.record("in", tool, sub_game, step=step, sender=sender)
        try:
            reply = call()
        except Exception as error:  # noqa: BLE001 - trace, then re-raise as-is
            wire_trace.record("in", f"{tool}:error", sub_game, step=step,
                              sender=sender, error=f"{type(error).__name__}: {error}")
            raise
        wire_trace.record("in", f"{tool}:ok", sub_game, step=step, sender=sender,
                          result=reply)
        return reply

    @mcp.tool
    def negotiate(message: dict[str, Any]) -> dict[str, Any]:
        """Open a match: exchange locked terms (contract, scent model, counts)."""
        return _inbound("negotiate", message, lambda: handler.negotiate(message))

    @mcp.tool
    def receive_turn(message: dict[str, Any]) -> dict[str, Any]:
        """Receive one turn message; the turn token travels with it."""
        return _inbound("receive_turn", message, lambda: handler.receive_turn(message))

    @mcp.tool
    def submit_audit(payload: dict[str, Any]) -> dict[str, Any]:
        """Receive the opponent's full end-of-game disclosure."""
        return _inbound("submit_audit", payload, lambda: handler.submit_audit(payload))

    @mcp.tool
    def receive_control(message: dict[str, Any]) -> dict[str, Any]:
        """Receive out-of-band signalling - the only channel a refusal can travel.

        Every tool in this wire shape returns ``{"ok": True}``, so a refusal
        cannot be a return value; it arrives as a pushed control message.
        """
        return _inbound("receive_control", message, lambda: handler.receive_control(message))

    return mcp


def serve(handler: InboundHandler, port: int, host: str = "0.0.0.0") -> None:  # noqa: S104
    """Run this peer's MCP server until the process stops.

    Bound to all interfaces so a tunnel (ngrok, Localtonet) can expose it to the
    public internet, which league play requires.
    """
    server = build_server(handler)
    server.run(transport="http", host=host, port=port)  # pragma: no cover - blocking call
