"""The shared game identity: the id and uid both peers must derive alike.

Split from :mod:`interop` when documenting the series label pushed that file
past the 150-line law - and the seam was already there. Everything in
``interop`` is about the CONTENT two teams agree on (terms, locked models,
signatures); this is about NAMING the game that content is played in. They
fail differently too: a terms disagreement refuses the handshake loudly, while
an identity collision plays six clean sub-games and only surfaces in the
league's inbox, wearing a valid schema.
"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .config_io import canonical_json


def derive_game_ids(
    terms: dict[str, Any], group_a: str, group_b: str, label: str = ""
) -> tuple[str, str]:
    """The shared ``(game_id, game_uid)`` - identical on both peers.

    The pair is SORTED: neither side names itself first, so both derive the
    same id with no round-trip. With no label the derivation is the kit's,
    unchanged and vector-pinned: the uid is a UUID over the first 16 bytes of
    ``SHA256(canonical(terms) + "|" + "|".join(sorted_pair))``.

    **The label exists because that derivation cannot tell two series apart.**
    Terms and pair are all it consumes, so every series the same two teams ever
    play carries one id and one uid - and when two of them settle on the same
    score they share the consensus hash too. sharNamr spotted it in our shared
    artifacts (2026-08-17): their run 4 and run 8 were both 77-77 / 3-3, making
    two complete series byte-indistinguishable at the identity level. Harmless
    between two inboxes; in the league's inbox it is a rule #35 conflict
    wearing a valid schema, and a counted game the grader cannot tell from a
    rehearsal.

    A label is therefore folded into BOTH halves, by a rule stated plainly so
    an opponent can implement the identical thing from this docstring alone::

        game_id  = "<a>-vs-<b>-<label>"
        game_uid = UUID(SHA256(canonical(terms) + "|" + game_id)[:16])

    The unlabelled path keeps ``"|".join(pair)`` as its seed tail, so every
    artifact and vector already written still derives exactly as before.
    """
    pair = sorted([group_a, group_b])
    game_id = f"{pair[0]}-vs-{pair[1]}"
    seed_tail = "|".join(pair)
    if label:
        game_id = f"{game_id}-{label}"
        seed_tail = game_id
    seed = f"{canonical_json(terms)}|{seed_tail}"
    game_uid = str(uuid.UUID(bytes=hashlib.sha256(seed.encode("utf-8")).digest()[:16]))
    return game_id, game_uid
