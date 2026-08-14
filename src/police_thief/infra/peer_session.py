"""One MCP session to the opponent, held open and reopened when it breaks.

A tunnel is not a LAN. Behind ngrok or Localtonet the expensive part of a
message is not the message: it is the connection, and re-establishing one per
move is both slow and the largest source of failures we have actually
observed. So a peer keeps ONE session per opponent and sends every move down
it.

Held-open is not the same as trusted-forever. A free tunnel restarts, an idle
stream gets reaped, an agent reconnects under the same public URL; any of
those kills the session without killing the opponent. So a failed call always
*discards* the session before propagating, and the next attempt - the retry
:class:`~.mcp_client.PeerClient` already owns - reconnects on a clean one.
That is the difference between a hiccup costing one retry and costing a
technical loss.

The headers matter too: ngrok's free tier answers a request it takes for a
browser with an interstitial HTML page rather than the peer, and
``ngrok-skip-browser-warning`` is the documented way to say we are not one.
It is inert against every other host.
"""

from __future__ import annotations

import contextlib
from typing import Any

from .net_errors import describe
from .transport import TransportError

#: Sent on every call: harmless everywhere, and it stops ngrok's free tier
#: from answering our peer's tool call with its browser-warning page.
TUNNEL_HEADERS = {"ngrok-skip-browser-warning": "true"}


class PeerSession:
    """A lazily-opened, reusable fastmcp client session to one peer URL."""

    def __init__(self, url: str, timeout: float = 30.0,
                 headers: dict[str, str] | None = None) -> None:
        """Describe the session; nothing is dialled until the first call."""
        self._url = url
        self._timeout = timeout
        self._headers = dict(TUNNEL_HEADERS if headers is None else headers)
        self._client: Any = None

    @property
    def connected(self) -> bool:
        """Whether a session is currently open to the peer."""
        return self._client is not None

    def _build(self) -> Any:
        """A fastmcp client bound to this peer, not yet connected.

        Raises:
            TransportError: if ``fastmcp`` is unavailable.
        """
        try:
            from fastmcp import Client
            from fastmcp.client.transports import StreamableHttpTransport
        except ImportError as error:  # pragma: no cover - dependency is declared
            raise TransportError("fastmcp is required for network play") from error
        return Client(
            StreamableHttpTransport(self._url, headers=self._headers),
            timeout=self._timeout,
            init_timeout=self._timeout,
        )

    async def connect(self) -> Any:
        """The open session, dialling the peer if there is not one yet.

        Raises:
            TransportError: naming the exception *type*, since the ones a
                tunnel raises carry no message at all.
        """
        if self._client is not None:
            return self._client
        client = self._build()
        try:
            await client.__aenter__()
        except Exception as error:
            self._client = None
            raise TransportError(
                f"could not open a session to {self._url} ({describe(error)})"
            ) from error
        self._client = client
        return client

    async def call(self, tool: str, arguments: dict[str, Any]) -> Any:
        """Call ``tool`` on the peer, discarding the session on any failure.

        Raises:
            TransportError: on any connection or protocol failure, so the
                PeerClient's retry-and-backoff can take over on a fresh
                session.
        """
        client = await self.connect()
        try:
            return await client.call_tool(tool, arguments)
        except Exception as error:
            await self.aclose()
            raise TransportError(
                f"{tool}: call to {self._url} failed ({describe(error)})"
            ) from error

    async def aclose(self) -> None:
        """Close the session if one is open; never raise while cleaning up."""
        client, self._client = self._client, None
        if client is None:
            return
        with contextlib.suppress(Exception):  # teardown must not mask the cause
            await client.__aexit__(None, None, None)
