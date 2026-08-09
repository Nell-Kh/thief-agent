"""Immutable structural constants of the game.

Only structural and physical constants live here. Every *tunable* quantitative
value (board size, quotas, scores, decay rate, timeouts) is read from
configuration - never hardcoded - per guidelines ch. 7.2 and the rulebook's
Mandatory Parameters Table.

Coordinate convention (ADR-4, rulebook ch. 3.3 default): cells are ``(row, col)``
pairs, the origin ``(0, 0)`` sits in the **top-left** corner and the row index
grows **downward**. North therefore decreases the row index.
"""

from typing import Final

# --- Roles -----------------------------------------------------------------
ROLE_POLICE: Final[str] = "police"
ROLE_THIEF: Final[str] = "thief"
ROLES: Final[tuple[str, ...]] = (ROLE_POLICE, ROLE_THIEF)

# --- Move set (rulebook ch. 3.4: four orthogonal directions or stay) --------
MOVE_NORTH: Final[str] = "N"
MOVE_SOUTH: Final[str] = "S"
MOVE_EAST: Final[str] = "E"
MOVE_WEST: Final[str] = "W"
MOVE_STAY: Final[str] = "STAY"

#: Deterministic tie-break order used by every brain (PRD_strategy).
MOVE_ORDER: Final[tuple[str, ...]] = (MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST, MOVE_STAY)

#: Displacement applied to ``(row, col)`` for each move. Diagonals do not exist.
MOVE_DELTAS: Final[dict[str, tuple[int, int]]] = {
    MOVE_NORTH: (-1, 0),
    MOVE_SOUTH: (1, 0),
    MOVE_EAST: (0, 1),
    MOVE_WEST: (0, -1),
    MOVE_STAY: (0, 0),
}

#: Moves that actually displace the agent (a barrier may only be placed on a
#: turn in which the cop forgoes movement).
STEPPING_MOVES: Final[tuple[str, ...]] = (MOVE_NORTH, MOVE_SOUTH, MOVE_EAST, MOVE_WEST)

# --- Game-phase state machine (rulebook ch. 8.3) ----------------------------
PHASE_WAITING: Final[str] = "WAITING_FOR_OPPONENT"
PHASE_COMPUTING: Final[str] = "COMPUTING_MOVE"
PHASE_COMMITTING: Final[str] = "COMMITTING"
PHASE_AWAITING_REVEAL: Final[str] = "AWAITING_REVEAL"
PHASE_VERIFYING: Final[str] = "VERIFYING"
PHASE_TECHNICAL_LOSS: Final[str] = "TECHNICAL_LOSS"

# --- Commit-reveal intent flag (rulebook ch. 5.3) ---------------------------
INTENT_TRUTH: Final[str] = "truth"
INTENT_LIE: Final[str] = "lie"
INTENTS: Final[tuple[str, ...]] = (INTENT_TRUTH, INTENT_LIE)

# --- Termination events (rulebook ch. 3.5 scoring table) --------------------
EVENT_CAPTURE: Final[str] = "capture"
EVENT_SURVIVAL: Final[str] = "survival"
EVENT_TIE: Final[str] = "tie"
EVENT_TECHNICAL_LOSS: Final[str] = "technical_loss"

# --- Lifecycle file names (rulebook Appendix F.3) ---------------------------
DECLARATION_FILE: Final[str] = "declaration_{game_id}.json"
CONFIG_FILE: Final[str] = "config_{game_id}_g{mini:02d}.json"
LOG_FILE: Final[str] = "log_{game_id}_g{mini:02d}.json"
RESULT_FILE: Final[str] = "result_{game_id}.json"

# --- Binding addresses (rulebook Appendix F.3; reference table, not tunable)-
AGENT_REPORT_ADDRESS: Final[str] = "rmisegal+uoh26finalgame@gmail.com"
LECTURER_ADDRESS: Final[str] = "rmisegal@gmail.com"

# --- Report delivery modes (rulebook ch. 9.3.3) -----------------------------
#: Build the message and park it in Gmail Drafts - the rehearsal path.
EMAIL_MODE_DRAFT: Final[str] = "draft"
#: Actually deliver. Rule #32 requires a counted game to be reported for real.
EMAIL_MODE_SEND: Final[str] = "send"

# --- Canonical serialization (rulebook ch. 5.3) -----------------------------
#: Separators guaranteeing byte-identical JSON on both peers before hashing.
CANONICAL_SEPARATORS: Final[tuple[str, str]] = (",", ":")
