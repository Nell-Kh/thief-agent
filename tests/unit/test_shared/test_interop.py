"""Tests for the shared game identity - the id and uid both peers must agree on."""

from __future__ import annotations

import hashlib
import uuid

from police_thief.constants import ROLE_POLICE
from police_thief.shared.config import ConfigManager
from police_thief.shared.config_io import canonical_json
from police_thief.shared.interop import derive_game_ids, terms_from_contract


def test_the_unlabelled_derivation_is_unchanged_and_still_pins_the_kit_vector() -> None:
    """Every artifact already written must still derive exactly as before."""
    terms = terms_from_contract(ConfigManager.load(ROLE_POLICE).contract)
    assert derive_game_ids(terms, "b", "a") == derive_game_ids(terms, "a", "b")
    game_id, _uid = derive_game_ids(terms, "yanell11", "sharNamr")
    assert game_id == "sharNamr-vs-yanell11"


def test_a_series_label_makes_two_series_distinguishable() -> None:
    """The rule-35 hazard sharNamr found in our shared artifacts (2026-08-17).

    ``derive_game_ids`` consumes only the terms and the group pair, so every
    series the same two teams ever play carried ONE id and ONE uid - and two
    series that settle on the same score share the consensus hash too, leaving
    them byte-indistinguishable at the identity level. A counted game the
    grader cannot tell from a rehearsal is a rule #35 conflict in a valid
    schema, so the label is folded into both halves.
    """
    terms = terms_from_contract(ConfigManager.load(ROLE_POLICE).contract)
    plain_id, plain_uid = derive_game_ids(terms, "yanell11", "sharNamr")
    one_id, one_uid = derive_game_ids(terms, "yanell11", "sharNamr", "counted-1")
    two_id, two_uid = derive_game_ids(terms, "yanell11", "sharNamr", "counted-2")

    assert one_id == "sharNamr-vs-yanell11-counted-1"
    assert len({plain_uid, one_uid, two_uid}) == 3, "each series needs its own uid"
    assert len({plain_id, one_id, two_id}) == 3


def test_the_unlabelled_uid_is_reproducible_from_its_own_documented_rule() -> None:
    """The branch a written spec loses, pinned so prose cannot drift from code.

    The two seed tails are different strings for the same pair -
    ``"sharNamr|yanell11"`` against ``"sharNamr-vs-yanell11"`` - so quoting only
    the labelled formula and adding "and the unlabelled case is unchanged"
    describes an implementation nobody can write. sharNamr took our sentence
    literally, derived ``a971be34-…`` where every shipped artifact carries
    ``9b80122e-…``, and told us before implementing it (2026-08-17).

    So both branches are pinned here, each recomputed from primitives::

        no label  -> UUID(SHA256(canonical(terms) + "|" + "|".join(sorted(pair)))[:16])
        label set -> UUID(SHA256(canonical(terms) + "|" + game_id)[:16])
    """
    terms = terms_from_contract(ConfigManager.load(ROLE_POLICE).contract)
    game_id, game_uid = derive_game_ids(terms, "yanell11", "sharNamr")
    pair_seed = f"{canonical_json(terms)}|{'|'.join(sorted(['yanell11', 'sharNamr']))}"
    expected = str(uuid.UUID(bytes=hashlib.sha256(pair_seed.encode("utf-8")).digest()[:16]))
    assert game_uid == expected

    # ...and the labelled formula applied to an UNLABELLED id is a DIFFERENT
    # uid. This is the counter-example itself, held so nobody "simplifies" the
    # two branches into one and silently renames every artifact ever written.
    id_seed = f"{canonical_json(terms)}|{game_id}"
    wrong = str(uuid.UUID(bytes=hashlib.sha256(id_seed.encode("utf-8")).digest()[:16]))
    assert wrong != game_uid


def test_a_labelled_uid_is_reproducible_from_the_documented_rule() -> None:
    """An opponent must be able to derive the identical pair from the docstring.

    The published rule is ``uid = UUID(SHA256(canonical(terms) + "|" + game_id))``
    over the first 16 bytes - recomputed here from primitives so the docstring
    and the code cannot drift apart.
    """
    terms = terms_from_contract(ConfigManager.load(ROLE_POLICE).contract)
    game_id, game_uid = derive_game_ids(terms, "yanell11", "sharNamr", "counted-1")
    seed = f"{canonical_json(terms)}|{game_id}"
    expected = str(uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]))
    assert game_uid == expected
