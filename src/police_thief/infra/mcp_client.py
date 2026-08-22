"""Outbound side of a peer: every call it makes to its opponent.

Each call is wrapped in a deadline (a request that outlives its expiry is a
failure, not patience) and a bounded retry with backoff. When the retries are
exhausted the caller is told plainly, so the runtime can take the emergency
exit to a technical loss instead of hanging.

The contract's budget - three tries, five seconds apart - is a *floor*, and it
was calibrated for a peer on the same network. A free tunnel drops and
re-establishes a connection on its own schedule, and a fifteen-second outage
under that budget costs a whole sub-game. So a delivery may additionally carry
a patience budget: keep re-offering the same message while the outage is
plausibly transient, bounded well inside the opponent's own turn-wait so a peer
that is genuinely gone still becomes a technical loss quickly. The opening
handshake deliberately does NOT use it - that wait belongs to the rendezvous
loop, which can tell "not started yet" from "refused".
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from . import wire_trace
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
        turn_patience_sec: float = 0.0,
    ) -> None:
        """Bind the client to a transport and the contract's timing rules."""
        self._transport = transport
        self._limits = limits
        self._sleep = sleep
        self._clock = clock
        self._turn_patience = max(0.0, turn_patience_sec)
        self._deadlines = DeadlineTracker(network.response_timeout_sec, clock=clock)

    @property
    def deadlines(self) -> DeadlineTracker:
        """The tracker stamping an expiry on every outgoing request."""
        return self._deadlines

    @property
    def turn_patience_sec(self) -> float:
        """Extra seconds a turn or audit delivery keeps retrying a silent peer."""
        return self._turn_patience

    def call(self, tool: str, payload: dict[str, Any], patience_sec: float = 0.0) -> dict[str, Any]:
        """Send one message, retrying transient failures within the budget.

        Raises:
            PeerUnreachableError: once every attempt has failed. The caller
                must treat this as a failure and close the turn, never as a
                reason to keep waiting.
            DeadlineExpiredError: if a reply arrives after the expiry.
        """
        floor = self._limits.max_retries
        patient_until = self._clock() + patience_sec
        last_error: Exception | None = None
        attempt = 0
        # Best-effort, opt-in via PT_WIRE_TRACE; "" when tracing is off. Lets the
        # trace name which endpoint each outbound call went to (their cop vs
        # their thief), which is exactly what the g03 post-mortem was missing.
        peer = (getattr(self._transport, "peer_url", "")
                or getattr(self._transport, "url", "") or "")
        step = payload.get("step") if isinstance(payload, dict) else None
        while True:
            attempt += 1
            label = f"{tool}#{attempt}"
            self._deadlines.start(label)
            wire_trace.record("out", tool, peer=peer, step=step, result=f"attempt {attempt}")
            try:
                reply = self._transport.send(tool, payload)
            except TransportError as error:
                last_error = error
                self._deadlines.clear()
                wire_trace.record("out", f"{tool}:error", peer=peer, step=step,
                                  error=f"{type(error).__name__}: {error}")
                if attempt >= floor and self._clock() >= patient_until:
                    break
                self._sleep(self._limits.retry_backoff_sec)
                continue
            self._deadlines.check(label)
            self._deadlines.complete(label)
            wire_trace.record("out", f"{tool}:ok", peer=peer, step=step, result=reply)
            return reply
        wire_trace.record("out", f"{tool}:unreachable", peer=peer, step=step,
                          error=str(last_error))
        raise PeerUnreachableError(
            f"{tool}: opponent unreachable after {attempt} attempts ({last_error})"
        )

    def negotiate(self, terms: dict[str, Any]) -> dict[str, Any]:
        """Open the match by offering our locked terms."""
        return self.call("negotiate", terms)

    def send_turn(self, wire: dict[str, Any]) -> dict[str, Any]:
        """Deliver one turn message; the turn token travels with it."""
        return self.call("receive_turn", wire, self._turn_patience)

    def submit_audit(self, disclosure: dict[str, Any]) -> dict[str, Any]:
        """Hand over the full log - payloads and nonces - for the mutual audit."""
        return self.call("submit_audit", disclosure, self._turn_patience)
