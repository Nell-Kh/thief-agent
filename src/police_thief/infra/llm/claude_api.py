"""The cloud provider: a small Claude model (Haiku) over the Anthropic API.

Real token consumption, measured from the API's own usage numbers and counted
against the agreed series budget. The API key comes from the environment only
(``ANTHROPIC_API_KEY``) - never from code or configuration files.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import (
    STYLE_VAGUE,
    HintProvider,
    HintRequest,
    ProviderError,
    clip_words,
    direction_word,
)
from .ledger import TokenLedger

DEFAULT_MODEL = "claude-haiku-4-5"


def anthropic_key() -> str | None:
    """The API key: process environment first, then the checkout's ``.env``.

    ``.env-example`` always said "copy to .env and fill in", but nothing ever
    read the copy - the game only saw a key `export`ed in the same shell, a
    dance that cost a live rehearsal its tokens when a placeholder overwrote
    the real key. One narrow loader closes the gap: this single variable,
    from the working directory's ``.env``, template placeholders ignored.
    """
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    env_file = Path.cwd() / ".env"
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("ANTHROPIC_API_KEY="):
            value = line.strip().split("=", 1)[1].strip().strip("'\"")
            if value and not value.startswith("<"):
                return value
    return None

SYSTEM_PROMPT = (
    "You are the {role} in a cops-and-robbers chase set in {area}. "
    "Write ONE taunting hint of at most {max_words} words claiming you moved "
    "{direction}. Mention a real landmark of {area}. Output only the hint text."
)

VAGUE_SYSTEM_PROMPT = (
    "You are the {role} in a cops-and-robbers chase set in {area}. "
    "Write ONE taunting hint of at most {max_words} words that gives away "
    "NOTHING about where you are or moved - no directions (north/south/east/"
    "west, up/down, left/right), no movement claims. Pure atmosphere. Mention "
    "a real landmark of {area}. Output only the hint text."
)


class ClaudeApiProvider(HintProvider):
    """Generates hints with a small cloud model; every token is metered."""

    name = "claude_api"

    def __init__(self, model: str, ledger: TokenLedger, timeout_sec: float = 10.0) -> None:
        """Bind the provider to a model, the consumption ledger and a hard timeout.

        Args:
            timeout_sec: wall-clock ceiling on one hint request. The verbal
                layer is decoration; the move is pure Python and already
                decided. A hint that has not arrived in time must lose to the
                template, never hold the turn.
        """
        self._model = model or DEFAULT_MODEL
        self._ledger = ledger
        self._timeout_sec = timeout_sec
        self._client = None

    def _get_client(self):
        """Build the SDK client lazily so imports never require a key.

        The client is bound to a request timeout and zero SDK-level retries:
        the default is minutes of patient back-off, which on a bad connection
        would hold our turn past the opponent's watchdog and hand them a
        technical loss over a taunt. One try, then the template covers it.

        Raises:
            ProviderError: if the SDK or the API key is unavailable.
        """
        if self._client is not None:
            return self._client
        key = anthropic_key()
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not set (environment or .env)")
        try:
            import anthropic
        except ImportError as error:  # pragma: no cover - dependency is declared
            raise ProviderError("anthropic SDK is not installed") from error
        self._client = anthropic.Anthropic(
            api_key=key, timeout=self._timeout_sec, max_retries=0
        )
        return self._client

    def generate(self, request: HintRequest) -> str:
        """Ask the model for one hint; measure and clip the result.

        Raises:
            ProviderError: on any API failure - the chain falls back to the
                template so the game continues.
        """
        client = self._get_client()
        claimed = request.claimed_direction()
        if request.style == STYLE_VAGUE or claimed is None:
            system = VAGUE_SYSTEM_PROMPT.format(
                role=request.role,
                area=request.map_area or "a nameless city",
                max_words=request.max_words,
            )
        else:
            system = SYSTEM_PROMPT.format(
                role=request.role,
                area=request.map_area or "a nameless city",
                max_words=request.max_words,
                direction=direction_word(claimed),
            )
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=60,
                system=system,
                messages=[{"role": "user", "content": f"Step {request.step}. The hint:"}],
            )
        except Exception as error:
            raise ProviderError(f"claude_api call failed: {error}") from error
        usage = getattr(response, "usage", None)
        self._ledger.record(
            step=request.step,
            provider=self.name,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
        )
        text = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        if not text.strip():
            raise ProviderError("claude_api returned no text")
        return clip_words(text.strip(), request.max_words)
