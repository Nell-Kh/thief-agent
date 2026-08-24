"""The filed report must settle under the CONFIGURED scope, not the kit default.

G010 (2026-08-24) forked because ``merge_series``/``series_result`` called
``result_payload`` without a profile: config declared ``settlement_scope = "uid"``
but the filer fell back to the kit ``DEFAULT`` and filed a kit-scope hash, while
uoh-ay26 filed the uid hash. For a friendly that was papered over; for a counted
series it is rule #35 - a zero for both teams. These tests pin that
``result_payload`` honours the profile it is handed, using the real G010 rows and
the two hashes both teams actually computed that night.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from police_thief.infra.email.reports import result_payload  # noqa: E402
from police_thief.shared.interop_profile import resolve  # noqa: E402

_GAME_ID = "uoh-ay26-vs-yanell11-G010"
_GAME_UID = "9d720049-dd3d-6ee2-a7db-67f17fb78f2d"

#: The two hashes both teams computed for G010, live that night.
_UID_SHA = "b34f8e46f16e19009f7b214f04c619edfd98b7023eccedabf62eb3e09b51c9fa"
_KIT_SHA = "b7f1130440f328d43a99a82401023a4627a88c39a894a6a7b3e012992c66d3cc"


def _rows() -> list[dict]:
    """The six settled G010 rows, with every field result_payload reads."""
    rows = []
    for n in range(1, 7):
        police = n % 2 == 1  # we were police on the odd windows
        rows.append({
            "sub_game_number": n,
            "roles": {"uoh-ay26": "thief" if police else "police",
                      "yanell11": "police" if police else "thief"},
            "result": "capture" if police else "survival",
            "winner_group": "yanell11",
            "score": {"uoh-ay26": 5, "yanell11": 20 if police else 10},
            "tie": False,
            "tokens": {"uoh-ay26": 0, "yanell11": 1000},
            "audit": {"log_verified": True, "tampered": False},
        })
    return rows


def _sha(profile) -> str:
    result = result_payload(
        game_uid=_GAME_UID, game_id=_GAME_ID, links={}, timezone="Asia/Jerusalem",
        group_ids=sorted(["yanell11", "uoh-ay26"]), sub_games=_rows(),
        tie_score=2, games_played={"yanell11": 2, "uoh-ay26": 0},
        first_meeting=False, counted=False, recipient="", profile=profile,
    )
    return result["mutual_agreement"]["sha256"]


def test_uid_profile_files_the_uid_hash() -> None:
    """A uid-configured filer reproduces uoh-ay26's native G010 hash."""
    assert _sha(resolve(settlement_scope="uid")) == _UID_SHA


def test_kit_profile_files_the_kit_hash() -> None:
    """The kit default is a genuinely different hash - the fork we must not ship."""
    assert _sha(resolve(settlement_scope="kit")) == _KIT_SHA


def test_the_two_scopes_do_not_collide() -> None:
    """Belt and braces: the whole point is that the scope choice changes the hash."""
    assert _UID_SHA != _KIT_SHA
