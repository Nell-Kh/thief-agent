"""The pheromone scent field: emission, decay, and the pre-series lock.

Every time an agent moves *or stays*, a scent field of size
``pheromone_grid_size`` (5x5) forms around its cell: the centre takes
``pheromone_center_intensity`` (0.9) and intensity falls radially exactly as
printed in the rulebook's Figure 4. At the end of every **full turn** - after
both agents have completed their moves - all traces decay by ``pheromone_decay``
(rho = 0.10). The update rule, verbatim from chapter 4:

    tau_ij(t+1) = max(0, (1 - rho) * tau_ij(t) + delta_tau_ij)

The scent is a natural, uncontrollable phenomenon: an agent cannot plant a
false trail; each side emits its own field and *reads only the opponent's*.
Before a series, both teams must exchange this exact model - formula plus a
concrete numeric example - and lock it with a SHA-256 hash; this module can
produce that canonical lock (rulebook ch. 4.5).
"""

from __future__ import annotations

from ..shared.config_io import sha256_of
from ..shared.interop_profile import DEFAULT, InteropProfile
from ..shared.schema import PheromoneConfig
from .board import Cell

#: Figure 4's printed intensities, VERBATIM, keyed by the sorted absolute
#: offsets from the emission centre. A lookup, never arithmetic: computing
#: these (e.g. ``0.9 * 42 / 90``) lands on ``0.42000000000000004`` - one IEEE
#: bit away from the printed ``0.42`` - and the league's interop kit pins the
#: printed doubles byte-exactly (vectors/scent_book_v3.json).
EMISSION_KERNEL: dict[tuple[int, int], float] = {
    (0, 0): 0.9,
    (0, 1): 0.62,
    (1, 1): 0.42,
    (0, 2): 0.2,
    (1, 2): 0.14,
    (2, 2): 0.04,
}

#: The centre intensity the verbatim kernel is printed for (App. F: fixed).
KERNEL_CENTER = 0.9

#: The formula string locked before a series, as the two teams agree it.
FORMULA = "tau_ij(t+1) = max(0, (1 - rho) * tau_ij(t) + delta_tau_ij)"


def emission_delta(config: PheromoneConfig, source: Cell, cell: Cell) -> float:
    """The fresh intensity ``delta_tau`` that ``source`` writes onto ``cell``.

    Zero outside the emission window. The window is square, spanning
    ``pheromone_grid_size`` cells per side around the source.
    """
    reach = config.grid_size // 2
    d_row = abs(cell[0] - source[0])
    d_col = abs(cell[1] - source[1])
    if d_row > reach or d_col > reach:
        return 0.0
    value = EMISSION_KERNEL[(min(d_row, d_col), max(d_row, d_col))]
    if config.center_intensity != KERNEL_CENTER:  # scaled only off the fixed default
        value = value * config.center_intensity / KERNEL_CENTER
    return value


class ScentField:
    """One agent's scent field, as its opponent perceives it."""

    def __init__(
        self,
        board_size: int,
        config: PheromoneConfig,
        profile: InteropProfile = DEFAULT,
    ) -> None:
        """Create an empty field over a ``board_size`` x ``board_size`` grid."""
        self._size = board_size
        self._config = config
        self._profile = profile
        self._tau: dict[Cell, float] = {}

    @property
    def config(self) -> PheromoneConfig:
        """The locked emission-decay parameters this field obeys."""
        return self._config

    def intensity(self, cell: Cell) -> float:
        """Current scent intensity in ``cell`` (0.0 when quiet)."""
        return self._tau.get(cell, 0.0)

    def advance(self, agent_cell: Cell) -> None:
        """Apply one full turn: decay every trace, then add this turn's emission.

        The lower clamp is explicit in the book's formula. The UPPER clamp is a
        dialect: the book prints ``max(0, ...)`` and nothing else, while the
        kit's registered ``multiplicative_book_v1`` bounds tau at
        ``emit_intensity`` - a reading the book's own re-emission figure
        supports, since it plateaus while the agent stays present.

        It is not a rounding nicety. It bites on the first re-emission
        (``0.9*0.9 + 0.9 = 1.71`` clamps to ``0.9``, where unclamped it would
        converge on 9.0), and the field crosses the wire as ``smell_grid`` every
        turn, so a peer on the other reading sees numbers the shared locked
        model cannot produce.
        """
        survive = 1.0 - self._config.decay
        ceiling = self._config.center_intensity
        clamp_above = self._profile.clamp_scent_to_emit
        updated: dict[Cell, float] = {}
        for row in range(self._size):
            for col in range(self._size):
                cell = (row, col)
                fresh = emission_delta(self._config, agent_cell, cell)
                value = max(0.0, survive * self._tau.get(cell, 0.0) + fresh)
                if clamp_above:
                    value = min(ceiling, value)
                if value > 0.0:
                    updated[cell] = value
        self._tau = updated

    def snapshot(self) -> dict[Cell, float]:
        """A copy of every non-quiet cell - what the opponent samples."""
        return dict(self._tau)

    def expected_fresh_trail(self) -> float:
        """Intensity a one-turn-old trail should show: (1 - rho) * center.

        This is the yardstick of the lie-detection example: a declared path
        with no such residue exposes the declaration as false.
        """
        return (1.0 - self._config.decay) * self._config.center_intensity


def lock_payload(config: PheromoneConfig) -> dict:
    """The locked scent-model document - the kit-registered doc, verbatim.

    Registered as ``multiplicative_book_v1`` in the class interop kit; two
    teams running the same model from the same book must hash the same doc,
    which only happens when the doc's field set is pinned. Our engine's
    conformance to it is proven against the kit's fixtures in
    ``tests/interop/test_kit_vectors.py``.
    """
    from ..shared.interop import SCENT_MODEL_DOC

    return SCENT_MODEL_DOC


def lock_sha256(config: PheromoneConfig) -> str:
    """The SHA-256 both teams exchange to lock the scent model pre-series."""
    return sha256_of(lock_payload(config))
