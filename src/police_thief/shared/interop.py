"""League interop: the byte-exact constructions every team must share.

Source of truth: the class interop kit (copthief-league-protocol, MIT) and
the reference implementation it pins. Two clean-room codebases that hash the
"same" data differently both score zero at audit - so the flat signed terms,
the terms signature, the shared game ids and the locked-model declarations
below reproduce the reference byte-for-byte, and the kit's conformance
vectors are vendored into ``tests/vectors`` to prove it on every test run.
"""

from __future__ import annotations

import hashlib
from typing import Any

from .config_io import canonical_json, sha256_of
from .identity import derive_game_ids  # noqa: F401  (re-exported: the kit's own home for it)
from .interop_profile import DEFAULT, InteropProfile
from .schema import GameContract

#: Registered locked-model documents we declare at negotiation (kit SPEC §7).
#: The hashes are the kit registry's; a vendored-vector test re-derives them.
SCENT_MODEL_SHA256 = "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"
WIRE_SHAPE_SHA256 = "229ae6487a418c3fcb6da9be404de2f2533c288ebc228811bff6dedc4164d6f7"
INFO_MODE_SHA256 = "020947daeeb3f73494af9b04201326791742c7184085456e3517d21981ee1202"

#: The registered scent-model document itself (family multiplicative_book_v1)
#: - published, hashed, and declared by hash only (the doc never crosses the wire).
SCENT_MODEL_DOC: dict[str, Any] = {
    "family": "scent_model",
    "name": "multiplicative_book_v1",
    "params": {
        "cadence": "per_full_turn",
        "center_intensity": 0.9,
        "clamp": [0.0, 0.9],
        "decay": "multiplicative",
        "decay_rho": 0.1,
        "evaluation_order": "(1 - rho) * tau + delta, then clamp",
        "field_size": 5,
        "initial_field": "empty",
        "kernel": [
            [0.04, 0.14, 0.2, 0.14, 0.04],
            [0.14, 0.42, 0.62, 0.42, 0.14],
            [0.2, 0.62, 0.9, 0.62, 0.2],
            [0.14, 0.42, 0.62, 0.42, 0.14],
            [0.04, 0.14, 0.2, 0.14, 0.04],
        ],
        "kernel_source": "book v3.0.0 figure 4 — printed values, verbatim lookup",
        "order": "decay_then_deposit",
        "receiver_side_decay": False,
        "rounding_decimals": None,
        "transmitted": False,
        "update": "tau' = clamp((1 - rho) * tau + kernel_delta, 0, center_intensity)",
    },
    "example": {
        "clamped": 0.9,
        "delta": 0.62,
        "note": "the clamp case: a saturated cell decays, then takes an adjacent deposit",
        "raw": 1.4300000000000002,
        "tau": 0.9,
    },
}


def terms_from_contract(
    contract: GameContract, profile: InteropProfile = DEFAULT
) -> dict[str, Any]:
    """The flat signed terms - the reference's ``terms_from_config``.

    This exact key set (and nothing else) is what both peers sign and what
    the shared ``game_uid`` is derived from; deriving from a wider object
    silently forks the uid (observed live in the league, kit SPEC §6).

    Fourteen keys under the kit dialect, thirteen under the book: the kit adds
    ``min_center_intensity``, which is not an Appendix B field. Since
    :func:`negotiation.validate_terms` compares the whole object, a peer signing
    the other count is refused outright - which is the honest outcome, but only
    if we know which count we meant.
    """
    terms: dict[str, Any] = {
        "board_size": contract.board.grid_size,
        "smell_grid_size": contract.pheromones.grid_size,
        "decay_per_step": contract.pheromones.decay,
        "emit_intensity": contract.pheromones.center_intensity,
        "max_steps": contract.movement.max_moves,
        "barriers_max": contract.movement.max_barriers,
        "setting": contract.world.map_area,
        "hint_max_words": contract.world.hint_max_words,
        "axis_origin_corner": contract.board.axis_origin_corner,
        "axis_start_index": contract.board.axis_start_index,
        "thief_start": list(contract.board.thief_start),
        "cop_start": list(contract.board.cop_start),
        "num_games": contract.network.num_games,
    }
    if profile.terms_carry_min_center_intensity:
        terms["min_center_intensity"] = contract.pheromones.min_center_intensity
    return terms


def sign_terms(terms: dict[str, Any], nonce: str) -> str:
    """The agreement checksum: ``SHA256(canonical(terms) + "|" + nonce)``.

    Named "signature" on the wire because that is the kit's field name and
    changing it would break every conformant peer - but it is a keyed signature
    in neither name nor fact. ``terms``, ``nonce`` and the digest all travel in
    the same greeting, so anyone can recompute it; it detects corruption in
    transit, not forgery by the sender. Book ch. 5.5 asks for signing under a
    pre-supplied key, which this project does not implement (README section 8).
    """
    material = f"{canonical_json(terms)}|{nonce}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def scent_model_lock() -> str:
    """The declared scent-model hash - the registered doc, never an ad-hoc dict.

    A bare hash over a home-grown field set differs between two teams running
    the very same model, and they refuse each other for no reason (SPEC §7).
    """
    return sha256_of(SCENT_MODEL_DOC)


def negotiate_extras(
    role: str, sub_game_number: int, profile: InteropProfile = DEFAULT
) -> dict[str, Any]:
    """Locked-model, pairing and dialect declarations beside the signed terms.

    Pairing fields (SPEC §7.2, PROMOTED): ``role`` and ``sub_game_number``
    catch a mispairing at the only moment it is still visible - the
    handshake. Model hashes declare our physics; per the kit's refusal rule,
    an opponent that omits a family is never refused for silence.

    ``interop_profile`` and ``tie_award`` extend that idea to the four dialect
    forks and the tie-award reading. They are the difference between a
    disagreement you answer in a chat message before kickoff and one you
    discover as a mutual zero at the audit, so unlike the model families they
    refuse on a stated difference in either direction.
    """
    return {
        "role": role,
        "sub_game_number": sub_game_number,
        "scent_model_sha256": SCENT_MODEL_SHA256,
        "wire_shape_sha256": WIRE_SHAPE_SHA256,
        "info_mode_sha256": INFO_MODE_SHA256,
        **profile.declaration(),
    }
