"""Tests for the paid providers, with every external dependency mocked."""

from __future__ import annotations

import io
import json
import urllib.error
from types import SimpleNamespace

import pytest

from police_thief.infra.llm.base import HintRequest, ProviderError
from police_thief.infra.llm.claude_api import ClaudeApiProvider
from police_thief.infra.llm.claude_cli import ClaudeCliProvider
from police_thief.infra.llm.ledger import TokenLedger
from police_thief.infra.llm.ollama import OllamaProvider

REQUEST = HintRequest(
    role="thief", intent="lie", true_direction="S", map_area="New York", max_words=15, step=2
)


class FakeHttpReply(io.BytesIO):
    """A context-manager byte stream, standing in for urlopen's reply."""

    def __enter__(self) -> FakeHttpReply:
        """Enter the fake context, returning the response itself."""
        return self

    def __exit__(self, *_args) -> None:
        """Leave the fake context without suppressing anything."""
        return None


# --- ollama ----------------------------------------------------------------


def test_ollama_generates_meters_and_clips(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"response": " ".join(["word"] * 30), "prompt_eval_count": 11, "eval_count": 7}
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda *_a, **_k: FakeHttpReply(json.dumps(payload).encode()),
    )
    ledger = TokenLedger(budget=1000)
    hint = OllamaProvider(model="m", ledger=ledger).generate(REQUEST)
    assert len(hint.split()) == 15
    assert ledger.total == 18
    assert ledger.entries[0].provider == "ollama"


def test_ollama_unreachable_becomes_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a, **_k):
        """Refuse the connection, as an unreachable local model would."""
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", refuse)
    with pytest.raises(ProviderError, match="ollama call failed"):
        OllamaProvider(model="m", ledger=TokenLedger(budget=0)).generate(REQUEST)


def test_ollama_empty_reply_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen", lambda *_a, **_k: FakeHttpReply(b'{"response": ""}')
    )
    with pytest.raises(ProviderError, match="no text"):
        OllamaProvider(model="m", ledger=TokenLedger(budget=0)).generate(REQUEST)


# --- claude_api ------------------------------------------------------------


def test_claude_api_without_a_key_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
        ClaudeApiProvider(model="", ledger=TokenLedger(budget=0)).generate(REQUEST)


def test_claude_api_generates_and_meters_real_usage() -> None:
    ledger = TokenLedger(budget=1000)
    provider = ClaudeApiProvider(model="", ledger=ledger)
    response = SimpleNamespace(
        usage=SimpleNamespace(input_tokens=42, output_tokens=13),
        content=[SimpleNamespace(type="text", text="Heading north past Wall Street, hurry.")],
    )
    provider._client = SimpleNamespace(
        messages=SimpleNamespace(create=lambda **_k: response)
    )
    hint = provider.generate(REQUEST)
    assert "north" in hint.lower()
    assert ledger.total == 55


def test_claude_api_failure_becomes_a_provider_error() -> None:
    provider = ClaudeApiProvider(model="", ledger=TokenLedger(budget=0))

    def explode(**_k):
        """Fail loudly, so the caller's error handling is the thing under test."""
        raise RuntimeError("rate limited")

    provider._client = SimpleNamespace(messages=SimpleNamespace(create=explode))
    with pytest.raises(ProviderError, match="claude_api call failed"):
        provider.generate(REQUEST)


def test_claude_api_empty_reply_is_an_error() -> None:
    provider = ClaudeApiProvider(model="", ledger=TokenLedger(budget=0))
    response = SimpleNamespace(usage=None, content=[])
    provider._client = SimpleNamespace(messages=SimpleNamespace(create=lambda **_k: response))
    with pytest.raises(ProviderError, match="no text"):
        provider.generate(REQUEST)


# --- claude_cli ------------------------------------------------------------


def test_cli_missing_binary_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(ProviderError, match="not installed"):
        ClaudeCliProvider(ledger=TokenLedger(budget=0)).generate(REQUEST)


def test_cli_generates_and_estimates_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/claude")
    completed = SimpleNamespace(stdout="Slipping north by the docks tonight.\n", stderr="")
    monkeypatch.setattr("subprocess.run", lambda *_a, **_k: completed)
    ledger = TokenLedger(budget=1000)
    hint = ClaudeCliProvider(ledger=ledger).generate(REQUEST)
    assert "north" in hint.lower()
    assert ledger.total > 0


def test_cli_failure_becomes_a_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/claude")

    def explode(*_a, **_k):
        """Fail loudly, so the caller's error handling is the thing under test."""
        raise subprocess.TimeoutExpired(cmd="claude", timeout=45)

    monkeypatch.setattr("subprocess.run", explode)
    with pytest.raises(ProviderError, match="claude CLI failed"):
        ClaudeCliProvider(ledger=TokenLedger(budget=0)).generate(REQUEST)


def test_the_paid_provider_is_bound_to_a_timeout_and_no_sdk_retries(monkeypatch) -> None:
    """A stalled hint must never hold our turn past the opponent's watchdog.

    The SDK's default is a multi-minute retry ladder; a taunt is decoration
    while the move is already decided in pure Python, so one bounded try is
    the whole budget - the template covers whatever does not arrive.
    """
    import sys
    from types import SimpleNamespace

    from police_thief.infra.llm.claude_api import ClaudeApiProvider
    from police_thief.infra.llm.ledger import TokenLedger

    captured: dict = {}

    def fake_anthropic_client(**kwargs):
        """Capture the constructor kwargs and return a canned client."""
        captured.update(kwargs)
        return SimpleNamespace(messages=SimpleNamespace(create=lambda **_: None))

    monkeypatch.setitem(sys.modules, "anthropic",
                        SimpleNamespace(Anthropic=fake_anthropic_client))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-a-real-secret")

    provider = ClaudeApiProvider(model="m", ledger=TokenLedger(budget=100), timeout_sec=7.5)
    provider._get_client()  # noqa: SLF001 - asserting the client's construction
    assert captured["timeout"] == 7.5
    assert captured["max_retries"] == 0


def test_a_missing_key_fails_before_any_network_call() -> None:
    """No key must be an instant local refusal, not a connection attempt."""
    import os

    from police_thief.infra.llm.base import ProviderError
    from police_thief.infra.llm.claude_api import ClaudeApiProvider
    from police_thief.infra.llm.ledger import TokenLedger

    saved = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        provider = ClaudeApiProvider(model="m", ledger=TokenLedger(budget=100))
        with pytest.raises(ProviderError, match="ANTHROPIC_API_KEY"):
            provider._get_client()  # noqa: SLF001 - the guard under test
    finally:
        if saved is not None:
            os.environ["ANTHROPIC_API_KEY"] = saved
