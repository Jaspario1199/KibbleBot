"""The contract between the mission and the world it acts on.

``RobotBackend`` is the only surface the mission logic touches. Today the
simulator (:mod:`kibblebot.simworld`) implements it; tomorrow a real backend
driving motors, an auger, and a pump over serial will implement the same
methods, and the mission code will not change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .config import Station
from .geometry import Pose


class FaultType(Enum):
    """The ways a feeding action can go wrong."""

    BOWL_NOT_FOUND = "bowl_not_found"   # vision couldn't confidently find it
    KIBBLE_JAM = "kibble_jam"           # auger jammed
    PUMP_FAIL = "pump_fail"             # water pump failed / air-locked
    HOPPER_EMPTY = "hopper_empty"       # onboard kibble ran out mid-dose
    TANK_EMPTY = "tank_empty"           # onboard water ran out mid-dose
    STUCK = "stuck"                     # drive base wedged / wheels slipping
    DOCK_FAILED = "dock_failed"         # couldn't dock / reload


class FeedingFault(Exception):
    """Raised by a backend when an action fails. Carries enough context for the
    mission to decide whether to skip a station or abort to the dock."""

    def __init__(self, fault: FaultType, detail: str = "", station: Optional[str] = None):
        self.fault = fault
        self.station = station
        self.detail = detail
        super().__init__(f"{fault.value}"
                         + (f" @ {station}" if station else "")
                         + (f": {detail}" if detail else ""))


@dataclass(frozen=True)
class BowlObservation:
    """What the camera/depth sensor reports about a bowl."""

    found: bool
    food_g: float = 0.0     # sensed current kibble in the bowl
    water_ml: float = 0.0   # sensed current water in the bowl


@dataclass(frozen=True)
class DispenseResult:
    """Outcome of a single dispense, measured by the robot's load cell/flow."""

    dispensed: float        # grams or millilitres actually delivered
    bowl_after: float       # resulting level in the bowl
    capped: bool = False    # True if we stopped early (bowl full / supply low)


@dataclass(frozen=True)
class ResourceLevels:
    """A snapshot of every reservoir the mission cares about."""

    onboard_kibble_g: float
    onboard_water_ml: float
    battery_pct: float
    dock_kibble_g: float
    dock_water_ml: float


class RobotBackend(ABC):
    """Everything the mission needs the physical (or simulated) robot to do."""

    @abstractmethod
    def now(self) -> float:
        """Seconds since the start of the run (for telemetry timestamps)."""

    @abstractmethod
    def pose(self) -> Pose:
        ...

    @abstractmethod
    def drive_to(self, target: Pose) -> float:
        """Drive to ``target``. Returns travel time (s). May raise STUCK."""

    @abstractmethod
    def locate_bowl(self, station: Station) -> BowlObservation:
        """Use the camera to find the bowl and estimate its current levels."""

    @abstractmethod
    def dispense_kibble(self, station: Station, target_g: float, current_g: float) -> DispenseResult:
        """Top the food bowl up toward ``target_g`` (never past it or capacity).
        May raise KIBBLE_JAM or HOPPER_EMPTY."""

    @abstractmethod
    def dispense_water(self, station: Station, target_ml: float, current_ml: float) -> DispenseResult:
        """Top the water bowl up toward ``target_ml``. May raise PUMP_FAIL or
        TANK_EMPTY."""

    @abstractmethod
    def dock_and_reload(self) -> None:
        """Return to the dock, recharge, and reload the hopper + tank from the
        bulk supplies. May raise DOCK_FAILED."""

    @abstractmethod
    def levels(self) -> ResourceLevels:
        ...
