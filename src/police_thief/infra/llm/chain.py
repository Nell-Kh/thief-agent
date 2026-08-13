"""Provider composition: throttling, fallback, and construction from config.

Two wrappers implement the rulebook's cost discipline:

* :class:`ThrottledProvider` - the paid model runs only once every
  ``every_n_steps`` turns; the free template covers the rest.
* :class:`FallbackProvider` - any provider failure (network, key, quota,
  exhausted budget) silently falls back to the template, so the verbal layer
  can never cost a game.
"""

from __future__ import annotations

from ...shared.bucket import TokenBucket
from .base import HintProvider, HintRequest, ProviderError
from .ledger import TokenLedger
from .template import TemplateProvider


class FallbackProvider(HintProvider):
    """Try the primary provider; on any failure, use the backup."""

    name = "fallback"

    def __init__(self, primary: HintProvider, backup: HintProvider) -> None:
        """Wrap ``primary`` with ``backup`` as the safety net."""
        self._primary = primary
        self._backup = backup
        self.fallbacks_used = 0

    def generate(self, request: HintRequest) -> str:
        """Generate via the primary, falling back on :class:`ProviderError`."""
        try:
            return self._primary.generate(request)
        except ProviderError:
            self.fallbacks_used += 1
            return self._backup.generate(request)


class ThrottledProvider(HintProvider):
    """Run the expensive provider once every ``every_n_steps``; else the cheap one."""

    name = "throttled"

    def __init__(self, expensive: HintProvider, cheap: HintProvider, every_n_steps: int) -> None:
        """Wrap the pair; ``every_n_steps`` below 1 means never throttle."""
        self._expensive = expensive
        self._cheap = cheap
        self._every = max(1, every_n_steps)

    def generate(self, request: HintRequest) -> str:
        """Route the request by step number."""
        if request.step % self._every == 0:
            return self._expensive.generate(request)
        return self._cheap.generate(request)


class BudgetGuard(HintProvider):
    """Refuse paid calls once the agreed token budget is exhausted."""

    name = "budget_guard"

    def __init__(self, inner: HintProvider, ledger: TokenLedger) -> None:
        """Wrap a paid provider with the series budget."""
        self._inner = inner
        self._ledger = ledger

    def generate(self, request: HintRequest) -> str:
        """Delegate while budget remains; otherwise fail into the fallback.

        Raises:
            ProviderError: when the series token budget is exhausted.
        """
        if self._ledger.exhausted:
            raise ProviderError("series token budget exhausted")
        return self._inner.generate(request)


class RateLimitedProvider(HintProvider):
    """Refuse a paid call that would exceed the configured requests-per-minute.

    The token budget and this limit answer different questions - "have we spent
    too much in total?" versus "are we calling too fast right now?" - and only
    the first was enforced. That left `config/rate_limits.json`'s ``anthropic``
    block read by no code path at all: configuration that looked like a control
    and was not one (ADR-3; the guidelines' no-hardcoded-values rule cuts both
    ways, and a limit nothing reads is the mirror image of a hardcoded one).

    Refusing raises :class:`ProviderError`, so the surrounding fallback turns a
    burst into a free template hint rather than a failed turn or a 429.
    """

    name = "rate_limited"

    def __init__(self, inner: HintProvider, bucket: TokenBucket) -> None:
        """Wrap a paid provider with the outgoing-request bucket."""
        self._inner = inner
        self._bucket = bucket
        self.refusals = 0

    def generate(self, request: HintRequest) -> str:
        """Spend a token and delegate, or fail into the fallback.

        Raises:
            ProviderError: when the per-minute allowance is exhausted.
        """
        if not self._bucket.allow():
            self.refusals += 1
            raise ProviderError("verbal-layer rate limit reached; using the template")
        return self._inner.generate(request)


def build_provider(
    provider_name: str,
    every_n_steps: int,
    ledger: TokenLedger,
    model: str = "",
    timeout_sec: float = 10.0,
    requests_per_minute: int | None = None,
) -> HintProvider:
    """Assemble the provider chain the private TOML selects.

    ``template`` stands alone. Every paid mode is wrapped as:
    throttle(rate_limit(budget_guard(paid)), template) inside a final fallback
    to the template - the guarantees compose, and no paid call escapes all three.

    Args:
        timeout_sec: wall-clock ceiling on one paid request, so a stalled
            network can never hold a turn past the opponent's watchdog.
        requests_per_minute: outgoing-call ceiling from ``config/rate_limits.json``.
            ``None`` leaves the chain unlimited, which is what the pure-template
            path and most tests want.
    """
    template = TemplateProvider()
    if provider_name == "template":
        return template
    if provider_name == "ollama":
        from .ollama import OllamaProvider

        paid: HintProvider = OllamaProvider(model=model, ledger=ledger)
    elif provider_name == "claude_api":
        from .claude_api import ClaudeApiProvider

        paid = ClaudeApiProvider(model=model, ledger=ledger, timeout_sec=timeout_sec)
    elif provider_name == "claude_cli":
        from .claude_cli import ClaudeCliProvider

        paid = ClaudeCliProvider(ledger=ledger)
    else:
        raise ValueError(f"unknown verbal provider {provider_name!r}")
    guarded: HintProvider = BudgetGuard(paid, ledger)
    if requests_per_minute:
        guarded = RateLimitedProvider(guarded, TokenBucket.per_minute(requests_per_minute))
    throttled = ThrottledProvider(guarded, template, every_n_steps)
    return FallbackProvider(throttled, template)


def effective_model(provider_name: str, model: str) -> str:
    """The model that will ACTUALLY produce hints on this machine, right now.

    Declarations and Step-0 records used to stamp the *configured* model,
    which read as a lie whenever the paid provider silently fell back: a
    grader sees "claude-3-5-haiku" beside zero tokens. This answers with the
    truth of the moment - the configured model only when its prerequisite
    (an API key, an installed CLI) is present, and an explicit fallback
    label naming what is missing otherwise.
    """
    import os
    import shutil

    if provider_name == "claude_api":
        chosen = model or "claude-3-5-haiku-latest"
        if os.environ.get("ANTHROPIC_API_KEY"):
            return chosen
        return f"template (fallback: {chosen} configured, ANTHROPIC_API_KEY absent)"
    if provider_name == "claude_cli":
        if shutil.which("claude"):
            return model or "claude (via CLI)"
        return "template (fallback: claude CLI not installed)"
    if provider_name == "ollama":
        return model or "ollama"
    return "template"
