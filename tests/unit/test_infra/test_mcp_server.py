"""Tests for the MCP server adapter over the ADR-7 tool set."""

from __future__ import annotations

import asyncio

import pytest

from police_thief.infra.mcp_server import TOOL_NAMES, build_server
from police_thief.services.inbound import InboundHandler

DIGEST = "c" * 64
SCENT = "d" * 64


@pytest.fixture
def handler() -> InboundHandler:
    """An inbound handler with minimal terms, for wire-level checks."""
    return InboundHandler(our_terms={"board_size": 7}, our_extras={}, expect_role="thief")


def _tools(server) -> dict:
    """Resolve the server's registered tools without a running event loop."""
    return {tool.name: tool for tool in asyncio.run(server.list_tools())}


def test_the_server_exposes_the_reference_tool_set(handler: InboundHandler) -> None:
    assert set(TOOL_NAMES) == {"negotiate", "receive_turn", "submit_audit", "receive_control"}
    assert set(TOOL_NAMES) <= set(_tools(build_server(handler)))


def test_the_server_takes_the_peer_name(handler: InboundHandler) -> None:
    assert build_server(handler, name="my_peer").name == "my_peer"
    assert build_server(handler).name == "police_thief_peer"


def test_every_registered_tool_is_documented(handler: InboundHandler) -> None:
    """The schema an opponent reads must describe what each tool does."""
    tools = _tools(build_server(handler))
    for name in TOOL_NAMES:
        assert tools[name].description


def test_a_registered_tool_forwards_to_the_handler(handler: InboundHandler) -> None:
    """The adapter holds no logic of its own - it delegates every call."""
    wire = {
        "step": 1,
        "sender": "thief",
        "hint": "gone east",
        "smell_grid": {"1,1": 0.5},
        "commit": "a" * 64,
    }
    asyncio.run(build_server(handler).call_tool("receive_turn", {"message": wire}))
    assert handler.commitments[1] == "a" * 64


def test_the_kwarg_asymmetry_is_the_references(handler: InboundHandler) -> None:
    """submit_audit takes ``payload``; the other three take ``message``.

    It looks like an inconsistency and it is load-bearing: the interop kit
    verified it against the reference, and a peer sending the wrong keyword
    gets a schema fault instead of a game.
    """
    tools = _tools(build_server(handler))
    for name in ("negotiate", "receive_turn", "receive_control"):
        assert "message" in tools[name].parameters["properties"]
    assert "payload" in tools["submit_audit"].parameters["properties"]


def test_control_messages_are_queued_and_acknowledged(handler: InboundHandler) -> None:
    control = {"kind": "enable", "sender": "thief", "sub_game_number": 2}
    asyncio.run(build_server(handler).call_tool("receive_control", {"message": control}))
    assert handler.next_control() == control
    assert handler.next_control() is None
