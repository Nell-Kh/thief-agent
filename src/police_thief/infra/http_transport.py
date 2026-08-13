"""The real network transport: MCP over HTTP to the opponent's public URL.

During early development the URL points at localhost; for league play it is the
opponent's tunnel URL (ngrok, Localtonet) - nothing else changes, which is the
point of the transport abstraction. Reliability lives one layer up: the
PeerClient wraps every call in a deadline and a bounded retry, and the
orchestrator converts exhaustion into a clean technical loss.

One MCP session is held open for the transport's whole life. The first
version opened a fresh session per call - six HTTP requests per game turn -
and a live rehearsal over two free ngrok tunnels died mid-sub-game when both
accounts hit ngrok's requests-per-minute cap. Reuse cuts a turn to a single
request; a failed call drops the session so the next attempt reconnects.
"""

from __future__ import annotations

import asyncio
import contextlib
import threading
from typing import Any

from .transport import TransportError

#: Backstop for a single round-trip; the contract's own deadlines are shorter.
CALL_TIMEOUT_SEC = 90.0


class McpHttpTransport:
    """Delivers protocol messages to a remote peer's FastMCP server."""

    def __init__(self, url: str) -> None:
        """Bind the transport to the opponent's MCP endpoint.

        Args:
            url: e.g. ``http://127.0.0.1:8802/mcp`` in development, or a
                public ``https://...ngrok...`` address in the league.
        """
        if not url.startswith(("http://", "https://")):
            raise TransportError(f"opponent URL must be http(s), got {url!r}")
        self._url = url
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: Any = None

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
            return self._submit(self._call(tool, payload))
        except TransportError:
            raise
        except Exception as error:
            raise TransportError(f"{tool}: transport failure ({error})") from error

    def close(self) -> None:
        """End the persistent session and stop its event loop thread."""
        if self._loop is None:
            return
        with contextlib.suppress(Exception):  # a broken session cannot refuse to drop
            self._submit(self._disconnect())
        loop, self._loop = self._loop, None
        loop.call_soon_threadsafe(loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def _submit(self, coro: Any) -> Any:
        """Run ``coro`` on the transport's private event loop and wait for it."""
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            self._thread = threading.Thread(
                target=self._loop.run_forever, name="mcp-transport", daemon=True
            )
            self._thread.start()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(CALL_TIMEOUT_SEC)
        except TimeoutError as error:
            future.cancel()
            # a stuck session is a dead session - drop it without waiting on it
            asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
            raise TransportError(
                f"no reply from {self._url} within {CALL_TIMEOUT_SEC:.0f}s"
            ) from error

    async def _call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """One round-trip on the open session, reconnecting if none exists."""
        arg_name = "payload" if tool == "submit_audit" else "message"
        try:
            client = await self._connect()
            result = await client.call_tool(tool, {arg_name: payload})
        except TransportError:
            await self._disconnect()
            raise
        except Exception as error:
            await self._disconnect()
            raise TransportError(f"{tool}: call to {self._url} failed ({error})") from error
        return _extract_reply(result)

    async def _connect(self) -> Any:
        """Return the open client session, establishing it on first use."""
        if self._client is None:
            try:
                from fastmcp import Client
            except ImportError as error:  # pragma: no cover - dependency is declared
                raise TransportError("fastmcp is required for network play") from error
            client = Client(self._url)
            await client.__aenter__()
            self._client = client
        return self._client

    async def _disconnect(self) -> None:
        """Drop the session, if any, swallowing the errors of a dying peer."""
        client, self._client = self._client, None
        if client is not None:
            with contextlib.suppress(Exception):  # closing a dying peer, best-effort
                await client.__aexit__(None, None, None)


def _extract_reply(result: Any) -> dict[str, Any]:
    """Normalize a fastmcp call result into the plain dict our protocol uses."""
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return data
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        return structured.get("result", structured)
    raise TransportError(f"opponent returned an unreadable reply: {result!r}")
