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
