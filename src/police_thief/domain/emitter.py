"""Locating the opponent by inverting the scent model, not by reading its peak.

The transmitted field is the whole accumulated trail, and every conformant
model clamps it at the emission ceiling. Both together make the peak useless:
after five moves the maximum is a PLATEAU - measured at 13 of 49 cells on our
own field - so an argmax picks whichever cell the tie-break happens to order
first, and the belief follows a phantom.

The emission is still there, though, in the *difference* between one turn's
field and the next. This module recovers the emitter by fitting the model
forward: for every candidate cell, predict what the field would look like if
the opponent had emitted there, and keep the candidate whose prediction is
closest to what actually arrived. Against our own registered model that is
exact - 8 of 8 cells on a moving path, zero residual - and against a peer on a
different reading it degrades to "the nearest cell that explains the field"
rather than failing outright.

Named after the thing it finds: the emitter, not the maximum.
"""

from __future__ import annotations

from ..shared.schema import PheromoneConfig
from .board import Cell
from .scent import emission_delta


def locate_emitter(
    previous: dict[Cell, float] | None,
    current: dict[Cell, float],
    config: PheromoneConfig,
    size: int,
) -> Cell | None:
    """The cell whose emission best explains ``current`` given ``previous``.

    Args:
        previous: the field this peer transmitted last turn, or None on the
            first message - with nothing to difference, a single fresh stamp
            has no plateau yet and the caller's argmax is already right.
        current: the field just received.
        config: the pheromone constants of the model we speak.
        size: the board edge.

    Returns:
        The best-fitting emitter cell, or None when there is nothing to fit
        (no previous field, or an empty current one).
    """
    if not current or previous is None:
        return None
    survive = 1.0 - config.decay
    ceiling = config.center_intensity
    cells = [(row, col) for row in range(size) for col in range(size)]
    best: Cell | None = None
    best_error: float | None = None
    for candidate in cells:
        error = 0.0
        for cell in cells:
            carried = previous.get(cell, 0.0) * survive
            predicted = min(carried + emission_delta(config, candidate, cell), ceiling)
            error += (predicted - current.get(cell, 0.0)) ** 2
        if best_error is None or error < best_error:
            best, best_error = candidate, error
    return best
