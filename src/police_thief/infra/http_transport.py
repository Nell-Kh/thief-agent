"""The real network transport: MCP over HTTP to the opponent's public URL.

During early development the URL points at localhost; for league play it is the
opponent's tunnel URL (ngrok, Localtonet) - nothing else changes, which is the
point of the transport abstraction. Reliability lives one layer up: the
PeerClient wraps every call in a deadline and a bounded retry, and the
orchestrator converts exhaustion into a clean technical loss.

Two things here are shaped by the tunnel rather than by the protocol. The
session is held open across calls (:mod:`infra.peer_session`) instead of dialled
per message, and the calls cross into one long-lived event loop
(:mod:`infra.async_loop`) instead of an ``asyncio.run`` each. Against localhost
neither mattered; against a free tunnel, a connection per move was most of the
cost and most of the failures.
"""

from __future__ import annotations

import contextlib
from typing import Any

from .async_loop import shared_loop
from .net_errors import describe
from .peer_session import PeerSession
from .transport import TransportError

#: Grace on top of the per-call budget before the *calling* thread gives up.
#: The session's own timeout should always fire first and say why; this is the
#: backstop that guarantees the turn loop is never wedged by the loop thread.
THREAD_GRACE_SEC = 5.0


class McpHttpTransport:
    """Delivers protocol messages to a remote peer's FastMCP server."""

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        """Bind the transport to the opponent's MCP endpoint.

        Args:
            url: e.g. ``http://127.0.0.1:8802/mcp`` in development, or a
                public ``https://...ngrok...`` address in the league.
            timeout: per-call budget, normally the contract's
                ``response_timeout_sec`` - a reply that misses it is a failure.
        """
        if not url.startswith(("http://", "https://")):
            raise TransportError(f"opponent URL must be http(s), got {url!r}")
        self._url = url
        self._timeout = timeout
        self._session = PeerSession(url, timeout=timeout)

    @property
    def url(self) -> str:
        """The opponent endpoint this transport talks to."""
        return self._url

    def send(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the opponent's ``tool`` with ``payload`` and return its reply.

        Raises:
            TransportError: on any connection or protocol failure, so the
                PeerClient's retry-and-backoff can take over.
        """
        try:
            return shared_loop().run(
                self._call(tool, payload), timeout=self._timeout + THREAD_GRACE_SEC
            )
        except TransportError:
            raise
        except Exception as error:
            raise TransportError(f"{tool}: transport failure ({describe(error)})") from error

    async def _call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """One round-trip to the opponent's server on the shared session."""
        arg_name = "payload" if tool == "submit_audit" else "message"
        return _extract_reply(await self._session.call(tool, {arg_name: payload}))

    def close(self) -> None:
        """Drop the session to this peer; safe to call more than once.

        A series opens one session per sub-game, and the sub-game that has
        just been audited has no further use for its own.
        """
        with contextlib.suppress(Exception):  # teardown must never fail a match
            shared_loop().run(self._session.aclose(), timeout=THREAD_GRACE_SEC)


def _extract_reply(result: Any) -> dict[str, Any]:
    """Normalize a fastmcp call result into the plain dict our protocol uses."""
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured.get("result", structured)
    raise TransportError(f"opponent returned an unreadable reply: {result!r}")
