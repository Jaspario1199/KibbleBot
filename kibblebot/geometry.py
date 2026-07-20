"""Minimal 2D geometry: everything is metres and radians.

Kept dependency-free (stdlib ``math`` only) so the simulator and control logic
run anywhere Python does, including tiny single-board computers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def wrap_angle(theta: float) -> float:
    """Wrap an angle to the interval (-pi, pi]."""
    return math.atan2(math.sin(theta), math.cos(theta))


@dataclass(frozen=True)
class Pose:
    """A robot pose on the floor plan: position + heading."""

    x: float
    y: float
    theta: float = 0.0  # heading in radians, 0 = +x axis

    def distance_to(self, other: "Pose") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def bearing_to(self, other: "Pose") -> float:
        """Heading (radians) needed to face ``other`` from here."""
        return math.atan2(other.y - self.y, other.x - self.x)

    def heading_error_to(self, other: "Pose") -> float:
        """Smallest signed turn needed to point at ``other``."""
        return wrap_angle(self.bearing_to(other) - self.theta)

    def with_heading(self, theta: float) -> "Pose":
        return Pose(self.x, self.y, wrap_angle(theta))
