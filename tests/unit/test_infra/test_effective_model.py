"""Tests for the honest model declaration: stamp what actually runs.

A declaration reading "claude-3-5-haiku" beside zero consumed tokens is the
shape of a lie, even when the cause is only a missing key. These pin the
rule: the configured model is declared exactly when its prerequisite is
present, and the fallback label names what was missing.
"""

from __future__ import annotations

import pytest

from police_thief.infra.llm import effective_model


def test_a_keyed_api_declares_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert effective_model("claude_api", "claude-3-5-haiku-latest") == "claude-3-5-haiku-latest"


def test_a_keyless_api_declares_the_template_and_names_the_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    declared = effective_model("claude_api", "claude-3-5-haiku-latest")
    assert declared.startswith("template")
    assert "ANTHROPIC_API_KEY absent" in declared
    assert "claude-3-5-haiku-latest" in declared  # the intent stays visible


def test_the_template_provider_declares_template_whatever_is_configured() -> None:
    assert effective_model("template", "claude-3-5-haiku-latest") == "template"


def test_a_missing_cli_declares_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    import police_thief.infra.llm.chain as chain_module  # noqa: F401 - patched below

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert "not installed" in effective_model("claude_cli", "")


def test_a_present_cli_declares_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/claude")
    assert effective_model("claude_cli", "") == "claude (via CLI)"
