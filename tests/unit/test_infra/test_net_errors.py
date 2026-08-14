"""Tests for rendering a network failure that carries no message of its own."""

from __future__ import annotations

from police_thief.infra.net_errors import MAX_CHAIN, describe, name_of


class SilentError(Exception):
    """An exception that stringifies to nothing, like the ones a tunnel raises."""


class FakeGroupError(Exception):
    """Stands in for anyio's exception group, which 3.10 has no builtin for.

    Only the ``exceptions`` attribute matters here - that is what the walker
    looks for, and what a real ``BaseExceptionGroup`` exposes.
    """

    def __init__(self, message: str, exceptions: list[BaseException]) -> None:
        """Carry a message and the members raised underneath it."""
        super().__init__(message)
        self.exceptions = tuple(exceptions)


def test_an_exception_with_no_message_still_names_its_type() -> None:
    assert name_of(SilentError()) == "SilentError"


def test_an_exception_with_a_message_keeps_it() -> None:
    assert name_of(ValueError("boom")) == "ValueError: boom"


def test_the_empty_fastmcp_message_becomes_readable() -> None:
    """The exact failure that started this: a bare, message-less connect error."""
    try:
        try:
            raise SilentError
        except SilentError as inner:
            raise RuntimeError("Client failed to connect: ") from inner
    except RuntimeError as error:
        described = describe(error)
    assert described == "RuntimeError: Client failed to connect: <- SilentError"


def test_a_cause_chain_is_walked_to_the_root() -> None:
    try:
        try:
            try:
                raise OSError("connection reset")
            except OSError as root:
                raise SilentError from root
        except SilentError as middle:
            raise RuntimeError("wrapped") from middle
    except RuntimeError as error:
        described = describe(error)
    assert "OSError: connection reset" in described
    assert described.count("<-") == 2


def test_the_members_of_a_group_are_reported() -> None:
    """anyio raises groups; the interesting failure is inside one, not on it."""
    group = FakeGroupError("both streams died", [SilentError(), ValueError("late")])
    described = describe(group)
    assert "SilentError" in described
    assert "ValueError: late" in described


def test_the_chain_is_bounded_so_a_log_line_stays_a_line() -> None:
    error: Exception = ValueError("root")
    for index in range(MAX_CHAIN + 4):
        error = RuntimeError(f"layer {index}").with_traceback(None)
        error.__cause__ = ValueError(f"cause {index}")
    described = describe(error)
    assert described.count("<-") < MAX_CHAIN


def test_a_context_is_used_when_there_is_no_explicit_cause() -> None:
    """An error raised *during* handling still points at what it interrupted."""
    try:
        try:
            raise OSError("original")
        except OSError:
            raise SilentError  # noqa: B904 - the missing `from` IS the case under test
    except SilentError as error:
        described = describe(error)
    assert described == "SilentError <- OSError: original"
