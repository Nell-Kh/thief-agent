"""Tests for the honest model declaration and the narrow ``.env`` key loader.

A declaration reading a paid model name beside zero consumed tokens is the
shape of a lie, even when the cause is only a missing key. These pin the
rule: the configured model is declared exactly when its prerequisite is
present, and the fallback label names what was missing. And because a live
rehearsal lost its tokens to an `export`ed placeholder, the key can now
also live in the checkout's ``.env`` - loaded by one function, tested here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from police_thief.infra.llm import effective_model
from police_thief.infra.llm.claude_api import anthropic_key


@pytest.fixture
def keyless(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """No key in the environment and no .env in the working directory."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_a_keyed_api_declares_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert effective_model("claude_api", "claude-haiku-4-5") == "claude-haiku-4-5"


def test_a_keyless_api_declares_the_template_and_names_the_gap(keyless: Path) -> None:
    declared = effective_model("claude_api", "claude-haiku-4-5")
    assert declared.startswith("template")
    assert "ANTHROPIC_API_KEY absent" in declared
    assert "claude-haiku-4-5" in declared  # the intent stays visible


def test_the_template_provider_declares_template_whatever_is_configured() -> None:
    assert effective_model("template", "claude-haiku-4-5") == "template"


def test_a_missing_cli_declares_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert "not installed" in effective_model("claude_cli", "")


def test_a_present_cli_declares_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda _name: "/usr/bin/claude")
    assert effective_model("claude_cli", "") == "claude (via CLI)"


def test_the_environment_key_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
    assert anthropic_key() == "sk-ant-from-env"


def test_the_env_file_is_read_when_the_environment_is_bare(keyless: Path) -> None:
    (keyless / ".env").write_text(
        '# comment\nANTHROPIC_API_KEY="sk-ant-from-file"\n', encoding="utf-8"
    )
    assert anthropic_key() == "sk-ant-from-file"
    assert effective_model("claude_api", "claude-haiku-4-5") == "claude-haiku-4-5"


def test_the_template_placeholder_is_not_a_key(keyless: Path) -> None:
    (keyless / ".env").write_text(
        "ANTHROPIC_API_KEY=<your-anthropic-key>\n", encoding="utf-8"
    )
    assert anthropic_key() is None


def test_no_env_file_means_no_key(keyless: Path) -> None:
    assert anthropic_key() is None
