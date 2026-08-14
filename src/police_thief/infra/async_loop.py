"""One asyncio loop that outlives a single call.

``asyncio.run`` per message was the right shape against localhost and the
wrong one against a tunnel. Every outgoing game move paid for a fresh TCP and
TLS handshake, a fresh MCP session (initialize, initialized, the server
stream, the tool call, the shutdown - five HTTP requests to carry one move)
and, on Windows, a brand new event loop that was torn down again immediately.
Multiply that by a six-sub-game series and the peer is opening thousands of
short-lived connections through a free tunnel that would rather serve a few
long ones.

This module gives the process a single daemon-thread loop so a session can be
opened once and reused. The loop is a daemon: it must never be the reason a
finished series fails to exit.

The turn loop above stays synchronous - that is deliberate (see
:mod:`infra.transport`) - so calls cross into the loop thread and block with a
timeout. Blocking forever on a peer we do not control is the deadlock the
rulebook's ch. 8.4.1 forbids, so a timeout is mandatory, never optional.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

#: Guards lazy creation of the process-wide loop.
_LOCK = threading.Lock()
_SHARED: LoopThread | None = None


class LoopThread:
    """An asyncio event loop running on its own daemon thread."""

    def __init__(self, name: str = "mcp-loop") -> None:
        """Start the loop; it runs until :meth:`close` or process exit."""
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._serve, name=name, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        """Run the loop forever on this thread."""
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    @property
    def running(self) -> bool:
        """Whether the loop thread is still alive and accepting work."""
        return self._thread.is_alive() and not self._loop.is_closed()

    def run(self, coro: Coroutine[Any, Any, Any], timeout: float | None = None) -> Any:
        """Run ``coro`` on the loop thread and return its result.

        Raises:
            TimeoutError: if the coroutine outlives ``timeout``. The coroutine
                is cancelled first, so a slow peer cannot leave work running
                behind a caller that has already given up.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout)
        except FutureTimeout as error:
            future.cancel()
            raise TimeoutError(f"call exceeded its {timeout}s budget") from error

    def close(self, timeout: float = 5.0) -> None:
        """Stop the loop and wait briefly for the thread to finish."""
        if not self.running:
            return
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout)


def shared_loop() -> LoopThread:
    """The process-wide loop, created on first use.

    One loop for every peer session in the process: sessions are I/O-bound and
    idle most of the time, and a loop per transport would spawn a thread per
    sub-game for no gain.
    """
    global _SHARED
    with _LOCK:
        if _SHARED is None or not _SHARED.running:
            _SHARED = LoopThread()
        return _SHARED
