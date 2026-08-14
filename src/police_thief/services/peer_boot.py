"""Booting one peer process: server thread up, orchestrator wired, handshake.

This is the two-process mode the separation rule demands: each role runs this
boot in its own process, with its own configuration directory, reachable at its
own port - and reaches its opponent only through the opponent's URL. The full
turn loop plugs in with the protocol layer; the boot already proves the pipe:
serve, connect, shake hands, and fail *cleanly* when the opponent never answers.

**Startup is a rendezvous, not a single shot.** Two peers are started by two
people in two terminals, seconds or minutes apart, so the one that starts first
always finds nobody home. :class:`PeerClient`'s retry budget is deliberately
short (a *mid-match* silence must become a technical loss quickly, not hang the
league), which makes it exactly the wrong budget for the opening handshake. So
the boot polls for the opponent across a generous window, and - because the peer
that shakes hands first would otherwise exit while the other is still dialling -
lingers afterwards, still serving, until the opponent has had its turn.

The retry/backoff loop for the opening handshake lives in :mod:`rendezvous`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from ..infra.http_transport import McpHttpTransport
from ..infra.mcp_server import build_server
from ..shared.config import ConfigManager
from .orchestrator import Orchestrator
from .rendezvous import rendezvous

#: How long to keep looking for an opponent that has not been started yet.
DEFAULT_WAIT_SECONDS = 120.0

#: How long to keep serving after our own handshake lands, so the opponent's
#: probe can complete against us before this process exits.
DEFAULT_LINGER_SECONDS = 15.0


@dataclass(frozen=True)
class BootReport:
    """What happened when a peer booted and reached for its opponent."""

    role: str
    my_port: int
    opponent_url: str
    handshake_ok: bool
    detail: str


def build_peer(config: ConfigManager) -> Orchestrator:
    """Wire one peer's orchestrator against its configured opponent URL."""
    opponent_url = str(config.private_value("network", "opponent_url", ""))
    timeout = float(config.contract.network.response_timeout_sec)
    return Orchestrator(config, McpHttpTransport(opponent_url, timeout=timeout))


def start_server(orchestrator: Orchestrator, port: int, host: str = "0.0.0.0") -> threading.Thread:  # noqa: S104
    """Run this peer's MCP server in a daemon thread.

    Bound to all interfaces so a tunnel can expose it publicly; the thread dies
    with the process, and the watchdog owns crash handling above us.
    """
    server = build_server(orchestrator.inbound)

    def _serve() -> None:  # pragma: no cover - blocking network loop
        """Block forever running the FastMCP HTTP transport."""
        server.run(transport="http", host=host, port=port, show_banner=False)

    thread = threading.Thread(target=_serve, name=f"mcp-server-{port}", daemon=True)
    thread.start()
    return thread


def check_connectivity(
    config: ConfigManager,
    peer_id: str,
    games_played: int,
    wait_seconds: float = DEFAULT_WAIT_SECONDS,
    linger_seconds: float = DEFAULT_LINGER_SECONDS,
    announce: Callable[[str], None] = lambda _message: None,
    sleep: Callable[[float], None] = time.sleep,
) -> BootReport:
    """Boot a peer, serve, and rendezvous with the opponent.

    With the opponent reachable (localhost or through a tunnel), the handshake
    exchanges contract digests and game counts - whichever side starts first
    simply waits for the other. With the opponent dark for the whole window, the
    peer reports a clean failure instead of hanging, which is what the league
    requires.
    """
    my_port = int(config.private_value("network", "my_port", 8800))
    opponent_url = str(config.private_value("network", "opponent_url", ""))
    orchestrator = build_peer(config)
    start_server(orchestrator, my_port)
    reply, refusal = rendezvous(orchestrator, peer_id, games_played, wait_seconds,
                                announce=announce)

    if refusal is not None:  # they answered and said no - report it verbatim
        return BootReport(config.role, my_port, opponent_url, False, refusal)
    if reply is None:
        orchestrator.fail(f"opponent unreachable within {wait_seconds:.0f}s")
        heard = getattr(orchestrator.inbound, "opponent_terms", None) is not None
        detail = (
            "we RECEIVED their handshake but could not reach them back - "
            f"check [network].opponent_url ({opponent_url})"
            if heard
            else f"opponent unreachable after {wait_seconds:.0f}s - technical loss declared"
        )
        return BootReport(config.role, my_port, opponent_url, False, detail)

    known = orchestrator.inbound.opponent_games_played
    seen = f"; opponent declared {known} games" if known is not None else ""
    if linger_seconds > 0:
        announce(f"handshake done - serving {linger_seconds:.0f}s more so the opponent can finish")
        sleep(linger_seconds)
    return BootReport(config.role, my_port, opponent_url, True, f"handshake accepted{seen}")
