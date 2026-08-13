"""Outbound side of a peer: every call it makes to its opponent.

Each call is wrapped in a deadline (a request that outlives its expiry is a
failure, not patience) and a bounded retry with backoff. When the retries are
exhausted the caller is told plainly, so the runtime can take the emergency
exit to a technical loss instead of hanging.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from ..services.deadline import DeadlineTracker
from ..shared.schema import NetworkConfig, RateLimiterConfig
from .transport import Transport, TransportError


class PeerUnreachableError(RuntimeError):
    """Raised when the opponent could not be reached within the retry budget."""


class PeerClient:
    """Sends protocol messages to the opponent and returns its replies."""

    def __init__(
        self,
        transport: Transport,
        network: NetworkConfig,
        limits: RateLimiterConfig,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Bind the client to a transport and the contract's timing rules."""
        self._transport = transport
        self._limits = limits
        self._sleep = sleep
        self._deadlines = DeadlineTracker(network.response_timeout_sec, clock=clock)

    @property
    def deadlines(self) -> DeadlineTracker:
        """The tracker stamping an expiry on every outgoing request."""
        return self._deadlines

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send one message, retrying transient failures within the budget.

        Raises:
            PeerUnreachableError: once every attempt has failed. The caller
                must treat this as a failure and close the turn, never as a
                reason to keep waiting.
            DeadlineExpiredError: if a reply arrives after the expiry.
        """
        attempts = self._limits.max_retries
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            label = f"{tool}#{attempt}"
            self._deadlines.start(label)
            try:
                reply = self._transport.send(tool, payload)
            except TransportError as error:
                last_error = error
                self._deadlines.clear()
                if attempt < attempts:
                    self._sleep(self._limits.retry_backoff_sec)
                continue
            self._deadlines.check(label)
            self._deadlines.complete(label)
            return reply
        raise PeerUnreachableError(
            f"{tool}: opponent unreachable after {attempts} attempts ({last_error})"
        )

    def close(self) -> None:
        """Release the transport's persistent connection, when it holds one."""
        closer = getattr(self._transport, "close", None)
        if callable(closer):
            closer()

    def negotiate(self, terms: dict[str, Any]) -> dict[str, Any]:
        """Open the match by offering our locked terms."""
        return self.call("negotiate", terms)

    def send_turn(self, wire: dict[str, Any]) -> dict[str, Any]:
        """Deliver one turn message; the turn token travels with it."""
        return self.call("receive_turn", wire)

    def submit_audit(self, disclosure: dict[str, Any]) -> dict[str, Any]:
        """Hand over the full log - payloads and nonces - for the mutual audit."""
        return self.call("submit_audit", disclosure)
