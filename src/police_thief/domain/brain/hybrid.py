"""The hybrid cop: hunt while the hunt works, wall the moment it stalls.

The wall cop guarantees capture but pays ~25 steps even against thieves the
region hunt kills in ~9. Every extra step is two more messages over a
possibly-flaky tunnel. The hybrid opens in region-hunt mode and commits to
the wall - irreversibly - on the first of three tripwires: the thief's
region has not shrunk for :attr:`STALL_TURNS` turns (the dance signature),
the region is still above :attr:`EARLY_REGION` at step :attr:`EARLY_STEP`
(the open-field-evader signature), or the step :attr:`DEADLINE` passes.

Measured frontier (all 1900 start pairs, PERFECT INFORMATION): against
reference-style thieves the hybrid captures 1900/1900 in a mean of ~12
steps (wall: ~25). Against our own elite evader it converts 1891/1900 -
nine starts escape, which is why the hybrid is NOT the default: the pure
wall's 1900/1900-everything guarantee is.

That speed advantage DOES NOT TRANSFER to real play. Under belief (the
only condition a league match is ever played in) and from the contract's
fixed start, the hybrid is measurably *slower* than the wall:

===================  ==============  =================  ===============
cop                  vs BlindThief   vs EnhancedThief   vs EvadeThief
===================  ==============  =================  ===============
WallPoliceBrain      capture @28     capture @28        survival @34
HybridPoliceBrain    capture @34     capture @34        survival @34
===================  ==============  =================  ===============

The opening hunt burns tempo chasing a belief argmax that is still
diffuse, so the wall finishes later than it would have unopened - and the
elite evader survives against both. There is therefore no opponent class
for which the hybrid is the better league choice: the league default is
:class:`~police_thief.domain.brain.seal.SealPoliceBrain` (round 3), which
also captures the elite evader under belief - see ``seal.py``.
The class is kept because the perfect-information frontier it maps is a
real research result (notebook §9b) and its tests pin that behaviour.
"""

from __future__ import annotations

from ..brain.base import BrainView
from ..engine import Action
from .region import region_size
from .wall import WallPoliceBrain


class HybridPoliceBrain(WallPoliceBrain):
    """Opportunistic region hunt with an irreversible fallback to the wall."""

    #: Turns without a new region minimum before the wall is committed.
    STALL_TURNS = 2

    #: Commit if the region is still above EARLY_REGION at this step.
    EARLY_STEP = 4

    #: The region size a converging hunt should be below by EARLY_STEP.
    EARLY_REGION = 14

    #: Absolute step bound on hunting - the wall needs ~20 turns to finish.
    DEADLINE = 12

    def __init__(self, role: str, contract) -> None:
        """Start in hunt mode with no progress recorded yet."""
        super().__init__(role, contract)
        self._best_region = 10**9
        self._stalled = 0
        self._committed = False

    def _build_action(self, view: BrainView) -> Action | None:
        """The wall step, or None while the hunt still earns its keep.

        Commitment is one-way: flip-flopping between modes would donate the
        tempo of both. The three tripwires are checked every turn until the
        first one fires.
        """
        current = region_size(view.board, view.position, view.target)
        if current < self._best_region:
            self._best_region = current
            self._stalled = 0
        else:
            self._stalled += 1
        if not self._committed and not self._tripped(view.step, current):
            return None
        self._committed = True
        return super()._build_action(view)

    def _tripped(self, step: int, current_region: int) -> bool:
        """Whether any of the three commit tripwires has fired."""
        return (
            self._stalled >= self.STALL_TURNS
            or (step >= self.EARLY_STEP and current_region > self.EARLY_REGION)
            or step >= self.DEADLINE
        )
