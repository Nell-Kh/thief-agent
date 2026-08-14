"""Reading a network failure out loud, because the raw one says nothing.

A tunnelled peer that goes quiet produced the least useful line this project
has ever logged::

    receive_turn: call to https://...ngrok-free.dev/mcp failed
    (Client failed to connect: )

The parenthesis is empty, and that is not a bug in the logging - it is what
``str()`` returns for the exceptions a tunnel actually raises.
``anyio.ClosedResourceError``, ``anyio.EndOfStream`` and ``httpx.ReadError``
are all constructed with no arguments, so fastmcp's
``f"Client failed to connect: {exception}"`` interpolates nothing at all.
The one fact that would identify the fault - the exception's *type* - is the
one fact the message throws away.

So every failure crossing our transport is rendered here instead: the type
name always, the text when there is any, and the whole chain beneath it
(``__cause__``, ``__context__``, and the members of an ``ExceptionGroup``),
because the interesting error is usually two links down.
"""

from __future__ import annotations

#: How many links of an exception chain to print. Enough to reach the socket
#: error under a group under a wrapper; short enough to stay one log line.
MAX_CHAIN = 6


def _links(error: BaseException) -> list[BaseException]:
    """``error`` and what lies beneath it: causes, contexts, group members."""
    seen: set[int] = set()
    found: list[BaseException] = []
    queue: list[BaseException | None] = [error]
    while queue and len(found) < MAX_CHAIN:
        item = queue.pop(0)
        if item is None or id(item) in seen:
            continue
        seen.add(id(item))
        found.append(item)
        queue.extend(getattr(item, "exceptions", None) or ())
        queue.append(item.__cause__ or item.__context__)
    return found


def name_of(error: BaseException) -> str:
    """One link, rendered as ``Type: text`` - or bare ``Type`` when silent."""
    text = str(error).strip()
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


def describe(error: BaseException) -> str:
    """The whole chain on one line, outermost first, joined by ``<-``.

    This is what a caller should put in a log or an error message in place of
    ``str(error)``: an empty-message exception still names itself, so an
    operator learns whether the tunnel refused the connection, dropped it
    mid-stream, or answered with something unreadable.
    """
    return " <- ".join(name_of(link) for link in _links(error))
