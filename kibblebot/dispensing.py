"""The dosing math — the single most safety-relevant piece of logic.

Pure functions, no state, easy to unit-test to death. The whole "never overfill"
guarantee lives here: a dose is bounded by the target, by the bowl's physical
capacity, and by what the robot actually has onboard.
"""

from __future__ import annotations


def compute_dose(
    current: float,
    target: float,
    bowl_capacity: float,
    onboard_available: float,
    tolerance: float = 0.0,
) -> float:
    """How much to dispense to top a bowl up toward ``target``.

    The result is always ``>= 0`` and never pushes the bowl above ``target`` or
    above ``bowl_capacity``, and never exceeds ``onboard_available``.

    - If the bowl is already at/above target (dog didn't eat), returns 0.
    - If the remaining room is below ``tolerance``, returns 0 (not worth a
      dribble / within load-cell noise).
    """
    if current < 0 or target < 0 or bowl_capacity < 0 or onboard_available < 0:
        raise ValueError("dosing inputs must be non-negative")

    ceiling = min(target, bowl_capacity)
    room = ceiling - current
    if room <= tolerance:
        return 0.0
    return min(room, onboard_available)
