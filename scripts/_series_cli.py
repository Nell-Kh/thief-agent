"""Command-line surface for the counted/friendly series driver.

Split from ``friendly_series.py`` under the 150-line rule. Everything
opponent-specific is an argument so the driver itself carries no identity.
"""

from __future__ import annotations

import argparse

from _series_lib import OPENING_WAIT_SECONDS, TURN_PATIENCE_SECONDS


def parse_args() -> argparse.Namespace:
    """Command-line surface: everything opponent-specific is an argument."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--peer", required=True,
                        help="opponent's MCP URL (their COP endpoint, when they are role-split)")
    parser.add_argument("--peer-thief", default="",
                        help="a role-split opponent's THIEF endpoint; sub-games where they "
                             "play thief dial here instead of --peer (default: same address)")
    parser.add_argument("--opponent-group-id", required=True,
                        help="the group_id the opponent will declare; a mismatch aborts")
    parser.add_argument("--start-role", required=True, choices=["police", "thief"],
                        help="our role in sub-game 1; alternates each sub-game after")
    parser.add_argument("--rounds", type=int, default=6, help="sub-games in the series")
    parser.add_argument("--port", type=int, default=8801, help="port our MCP server binds")
    parser.add_argument("--host", default="127.0.0.1",
                        help="bind address; 0.0.0.0 for a direct remote connection")
    parser.add_argument("--public-url", default="",
                        help="our tunnel URL, recorded in the declaration artifact")
    parser.add_argument("--artifacts", default="", help="output directory for artifacts")
    parser.add_argument("--config-dir", default="",
                        help="alternate config/ directory (a second identity, for rehearsals)")
    parser.add_argument("--turn-patience", type=float, default=TURN_PATIENCE_SECONDS,
                        help="extra seconds a turn or audit delivery keeps retrying a "
                             "tunnel that has dropped; 0 restores the contract's bare "
                             "three-tries budget")
    parser.add_argument("--wait", type=float, default=OPENING_WAIT_SECONDS,
                        help="seconds to keep re-offering terms to an opponent that has "
                             "not started yet (the two-terminal gap)")
    parser.add_argument("--games-played", type=int, default=0,
                        help="counted games already played against this opponent (rule 37)")
    parser.add_argument("--series-label", default="",
                        help="a label distinguishing THIS series from every other against "
                             "the same opponent, agreed with them in writing (e.g. "
                             "'counted-1'). Folded into both game_id and game_uid: without "
                             "it the kit's derivation gives every series the same identity")
    parser.add_argument("--timezone", default="Asia/Jerusalem")
    parser.add_argument("--counted", action="store_true",
                        help="claim league credit; only arms when addressed to the "
                             "binding league address, and never for a friendly")
    return parser.parse_args()
