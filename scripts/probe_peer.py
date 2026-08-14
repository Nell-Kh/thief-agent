"""Dial a peer's MCP URL and say, in full, what happened.

A series is the worst place to discover that a tunnel is flaky: it costs a
sub-game per discovery and the log line it leaves behind - ``Client failed to
connect: `` with nothing after the colon - names neither the fault nor the
side at fault. This script is the same dial, alone, out loud, and repeatable.

It answers three separate questions that the series conflates:

* **Is the endpoint there at all?** One connection, the peer's tool list
  printed. A tunnel with nothing behind it, a wrong path, a stale URL and a
  peer that is simply not started all fail differently here and say so.
* **Does it STAY there?** ``--repeat`` dials N times and reports how many
  succeeded, how slow each was, and what each failure actually was. A tunnel
  that answers 9 times in 10 is the shape of failure that reads as "the
  opponent crashed" during a match, and it is invisible in a single probe.
* **Does a held-open session survive?** ``--hold`` keeps ONE session open and
  calls down it, which is how the peer now plays. A tunnel that reaps idle
  connections fails this and passes the others.

Usage::

    .venv/Scripts/python.exe scripts/probe_peer.py https://them.ngrok-free.dev/mcp
    .venv/Scripts/python.exe scripts/probe_peer.py <url> --repeat 20 --gap 3
    .venv/Scripts/python.exe scripts/probe_peer.py <url> --repeat 10 --hold

Nothing here plays a game or sends a turn: the probe only lists tools, so it is
safe to point at a live opponent mid-series.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from police_thief.infra.async_loop import shared_loop  # noqa: E402
from police_thief.infra.net_errors import describe  # noqa: E402
from police_thief.infra.peer_session import TUNNEL_HEADERS, PeerSession  # noqa: E402

#: Tool names a conformant league peer must expose (ADR-7).
EXPECTED = ("negotiate", "receive_turn", "submit_audit", "receive_control")


def parse_args() -> argparse.Namespace:
    """Command-line surface: a URL, and how hard to lean on it."""
    parser = argparse.ArgumentParser(description="Probe a peer's MCP endpoint.")
    parser.add_argument("url", help="the peer's MCP URL, e.g. https://x.ngrok-free.dev/mcp")
    parser.add_argument("--repeat", type=int, default=1, help="how many probes to run")
    parser.add_argument("--gap", type=float, default=2.0, help="seconds between probes")
    parser.add_argument("--timeout", type=float, default=30.0, help="per-probe budget")
    parser.add_argument("--hold", action="store_true",
                        help="reuse ONE session for every probe, as a match now does")
    return parser.parse_args()


async def _tools(session: PeerSession) -> list[str]:
    """The peer's advertised tool names, over an open session."""
    client = await session.connect()
    return sorted(tool.name for tool in await client.list_tools())


def probe(session: PeerSession, timeout: float) -> tuple[bool, float, str]:
    """One probe: ``(ok, elapsed_seconds, detail)`` - never raises."""
    started = time.monotonic()
    try:
        names = shared_loop().run(_tools(session), timeout=timeout + 5.0)
    except Exception as error:
        return False, time.monotonic() - started, describe(error)
    missing = [name for name in EXPECTED if name not in names]
    detail = f"tools: {', '.join(names) or '(none)'}"
    if missing:
        detail += f"  MISSING: {', '.join(missing)}"
    return not missing, time.monotonic() - started, detail


def run(args: argparse.Namespace) -> int:
    """Probe as instructed and print a verdict; return a process exit code."""
    print(f"probing {args.url}")
    print(f"  headers   : {TUNNEL_HEADERS}")
    print(f"  mode      : {'one held-open session' if args.hold else 'a fresh session each'}")
    held = PeerSession(args.url, timeout=args.timeout) if args.hold else None
    good = 0
    for index in range(1, args.repeat + 1):
        session = held or PeerSession(args.url, timeout=args.timeout)
        ok, elapsed, detail = probe(session, args.timeout)
        good += ok
        print(f"  #{index:<3} {'OK  ' if ok else 'FAIL'} {elapsed:6.2f}s  {detail}")
        if held is None:
            shared_loop().run(session.aclose(), timeout=5.0)
        if index < args.repeat:
            time.sleep(args.gap)
    if held is not None:
        shared_loop().run(held.aclose(), timeout=5.0)
    print(f"\n{good}/{args.repeat} probes succeeded")
    if good and good < args.repeat:
        print("An intermittent endpoint is the failure that reads as 'the opponent "
              "crashed' mid-series. Restart the tunnel agent before playing.")
    return 0 if good == args.repeat else 1


def main() -> None:
    """Entry point: probe, then exit non-zero if any probe failed."""
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
