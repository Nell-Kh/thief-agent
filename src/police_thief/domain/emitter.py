"""Locating the opponent by inverting the scent model, not by reading its peak.

The transmitted field is the whole accumulated trail, and every conformant
model clamps it at the emission ceiling. Both together make the peak useless:
after five moves the maximum is a PLATEAU - measured at 13 of 49 cells on our
own field - so an argmax picks whichever cell the tie-break happens to order
first, and the belief follows a phantom. Measured over a twelve-step path,
argmax locates the emitter 0 times out of 11; this module locates it 11.

The emission is still there, though, in the *difference* between one turn's
field and the next. This module recovers the emitter by fitting the model
forward: for every candidate cell, predict what the field would look like if
the opponent had emitted there, and keep the candidate whose prediction is
closest to what actually arrived.

Two things make that fit survive contact with a peer speaking a different
model, which is the ordinary case in a league of independent implementations:

* **The ceiling is observed, not assumed.** Our own model clamps accumulation
  at ``center_intensity``; a lawful peer may not, and NajAmjad's does not. A
  clamped *prediction* against an unclamped *field* is wrong at every cell
  above the ceiling, which drowns the signal - it cost 4 of 11 locations, and
  it inverted the fit statistic so badly that a bad fit scored better than a
  good one. When the arriving field exceeds our ceiling the peer has told us it
  does not clamp, and we stop clamping the prediction. That alone restores
  11/11 against their kernel.

* **A fit that explains nothing is refused.** The residual at the best
  candidate is compared against the null hypothesis - decay alone, no emitter
  anywhere. A real emission explains the field far better than nothing does
  (measured: ratio 0.000 against our own model, 0.07-0.13 against NajAmjad's
  subtractive-Chebyshev one), while an unreadable field does not (0.82-0.95
  against random noise). Below ``ACCEPT_RATIO`` we pin belief hard; above it we
  return None and leave the belief to the ordinary scent update, because a
  confident pin on a phantom is worse than no pin at all.

Named after the thing it finds: the emitter, not the maximum.
"""

from __future__ import annotations

from ..shared.schema import PheromoneConfig
from .board import Cell
from .scent import emission_delta

#: The best candidate must explain the field at least this much better than
#: "no emitter at all", or we decline to pin. Calibrated on three models: our
#: own scores 0.000, a foreign but lawful kernel 0.07-0.13, random noise
#: 0.82-0.95. Any threshold in (0.15, 0.8) separates them; 0.5 is the middle.
ACCEPT_RATIO = 0.5


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
        (no previous field, an empty current one) or when the best fit does
        not explain the field appreciably better than no emitter at all.
    """
    if not current or previous is None:
        return None
    cells = [(row, col) for row in range(size) for col in range(size)]
    survive = 1.0 - config.decay
    carried = {cell: previous.get(cell, 0.0) * survive for cell in cells}
    ceiling = observed_ceiling(current, config.center_intensity)
    null_error = _residual(carried, current, cells, None, config, ceiling)
    if null_error <= 0.0:
        return None
    best: Cell | None = None
    best_error: float | None = None
    for candidate in cells:
        error = _residual(carried, current, cells, candidate, config, ceiling)
        if best_error is None or error < best_error:
            best, best_error = candidate, error
    if best_error is None or best_error > null_error * ACCEPT_RATIO:
        return None
    return best


def observed_ceiling(current: dict[Cell, float], ours: float) -> float:
    """The clamp to predict under: ours, unless the field has already broken it.

    Our model bounds accumulation at ``center_intensity``. A peer is free to
    read chapter 4 without that bound - NajAmjad's ``subtractive_chebyshev_v1``
    does - and a field carrying a value above our ceiling is that peer saying
    so on the wire. Predicting under a clamp the sender does not apply makes
    every saturated cell wrong by an unbounded amount, so the evidence wins
    over the assumption.
    """
    if current and max(current.values()) > ours + 1e-6:
        return float("inf")
    return ours


def _residual(
    carried: dict[Cell, float],
    current: dict[Cell, float],
    cells: list[Cell],
    candidate: Cell | None,
    config: PheromoneConfig,
    ceiling: float,
) -> float:
    """Summed squared error of the forward model, with or without an emitter.

    ``candidate`` of None is the null hypothesis: decay carried the whole
    field and nobody emitted anywhere. It is the yardstick the best candidate
    has to beat, and it is what makes the acceptance test scale-free - both
    sides of the comparison move together when a peer's kernel is stronger or
    weaker than ours.
    """
    total = 0.0
    for cell in cells:
        predicted = carried[cell]
        if candidate is not None:
            predicted += emission_delta(config, candidate, cell)
        total += (min(predicted, ceiling) - current.get(cell, 0.0)) ** 2
    return total
