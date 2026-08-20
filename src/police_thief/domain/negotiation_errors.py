"""The one exception the handshake raises, in a module both halves can import.

:mod:`negotiation` and :mod:`model_locks` both raise it and ``model_locks`` is
imported BY ``negotiation``, so leaving the class in either one would close an
import cycle. It sits here instead - a module with no imports of its own can
never be half of one.
"""

from __future__ import annotations


class TermsRejectedError(RuntimeError):
    """Raised when the opponent's greeting must be refused."""
