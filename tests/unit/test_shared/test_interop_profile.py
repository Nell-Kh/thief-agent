"""The dialect must actually fork - and each side must stay itself.

A profile switch that quietly produced the same bytes under both readings would
be worse than no switch at all: it would document a choice the code does not
make. Every test here therefore pins a CONCRETE difference, not merely that the
setting is readable.
"""

from __future__ import annotations

import pytest

from police_thief.shared.interop_profile import (
    DEFAULT,
    PROFILE_BOOK,
    PROFILE_KIT,
    SCOPE_KIT,
    SCOPE_UID,
    TIE_AWARD_ADD,
    TIE_AWARD_SUBSTITUTE,
    TURN_ORDER,
    InteropProfileError,
    resolve,
)

KIT = resolve(PROFILE_KIT)
BOOK = resolve(PROFILE_BOOK)


def test_the_default_is_the_kit_dialect() -> None:
    """Our vendored vectors pass under kit; changing the default breaks them."""
    assert DEFAULT.name == PROFILE_KIT
    assert DEFAULT.tie_award == TIE_AWARD_ADD


def test_every_fork_actually_differs_between_the_two_dialects() -> None:
    """The four forks are the whole point - none may collapse."""
    assert KIT.nonce_inside_payload != BOOK.nonce_inside_payload
    assert KIT.clamp_scent_to_emit != BOOK.clamp_scent_to_emit
    assert KIT.settlement_spaced != BOOK.settlement_spaced
    assert (
        KIT.terms_carry_min_center_intensity != BOOK.terms_carry_min_center_intensity
    )
    assert KIT.default_setting != BOOK.default_setting


def test_the_book_dialect_matches_the_printed_rulebook() -> None:
    """Each book-side answer traces to a chapter, not to a preference."""
    assert BOOK.nonce_inside_payload is True      # ch. 5.3.1 printed sample
    assert BOOK.clamp_scent_to_emit is False      # ch. 4.3 has max(0, .) only
    assert BOOK.default_setting == "New York"     # App. F printed example
    assert BOOK.terms_carry_min_center_intensity is False  # not an App. B field


@pytest.mark.parametrize("bad", ["kitt", "boook", "reference", "rulebook", "none"])
def test_an_unrecognised_profile_refuses_rather_than_defaulting(bad: str) -> None:
    """A typo must never fall back to a default - that is the silent divergence."""
    with pytest.raises(InteropProfileError):
        resolve(bad)


@pytest.mark.parametrize("absent", ["", None])
def test_an_absent_profile_takes_the_kit_default(absent: str | None) -> None:
    """Absent is not a typo: a config with no [interop] section still runs."""
    assert resolve(absent).name == PROFILE_KIT


def test_an_unrecognised_tie_award_refuses() -> None:
    with pytest.raises(InteropProfileError):
        resolve(PROFILE_KIT, "average")


def test_the_tie_award_is_independent_of_the_dialect() -> None:
    """The kit does not settle it, so it must be selectable under either."""
    assert resolve(PROFILE_KIT, TIE_AWARD_SUBSTITUTE).tie_award_adds is False
    assert resolve(PROFILE_BOOK, TIE_AWARD_ADD).tie_award_adds is True


def test_the_declaration_carries_everything_a_peer_must_agree_on() -> None:
    """What is not declared cannot be refused, and forks silently instead."""
    declaration = KIT.declaration()
    assert declaration == {
        "interop_profile": PROFILE_KIT,
        "tie_award": TIE_AWARD_ADD,
        "turn_order": TURN_ORDER,
        "settlement_scope": SCOPE_KIT,
    }


def test_the_settlement_scope_is_independent_of_the_dialect() -> None:
    """Which object is hashed and how its bytes are spelled are two questions.

    uoh-ay26's preimage differs from the kit's in four ways at once - the bare
    label as ``game_id``, a ``game_uid``, no aggregate, and compact separators -
    so no combination of dialect and tie-award reaches it. It needs its own axis.
    """
    assert resolve(PROFILE_KIT, TIE_AWARD_ADD, SCOPE_UID).scope_carries_aggregate is False
    assert resolve(PROFILE_KIT, TIE_AWARD_ADD, SCOPE_KIT).scope_carries_aggregate is True
    # The kit dialect settles spaced - but never under the uid scope, which pins
    # compact as part of its own definition.
    assert resolve(PROFILE_KIT, TIE_AWARD_ADD, SCOPE_KIT).settlement_scope_spaced is True
    assert resolve(PROFILE_KIT, TIE_AWARD_ADD, SCOPE_UID).settlement_scope_spaced is False
    assert resolve(PROFILE_BOOK, TIE_AWARD_ADD, SCOPE_KIT).settlement_scope_spaced is False


def test_an_unknown_settlement_scope_is_refused_not_defaulted() -> None:
    """A typo must never quietly settle on the other team's hash."""
    with pytest.raises(InteropProfileError, match="settlement_scope"):
        resolve(PROFILE_KIT, TIE_AWARD_ADD, "uoh-ay26")


def test_case_and_whitespace_in_config_do_not_change_the_dialect() -> None:
    """A TOML edited by hand must not fork the protocol on stray whitespace."""
    assert resolve("  KIT  ").name == PROFILE_KIT
    assert resolve("Book").name == PROFILE_BOOK
