"""Everything about *this* house, *these* dogs, and the machine lives here.

A real deployment ships one ``HouseConfig``; the rest of the code is generic and
reads only from these objects, so adapting kibble-bot to a new home (or new
dogs) is a config change, not a code change. The values in :func:`default_house`
are the two-dog home from the design brief and are used by the demo and tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from .geometry import Pose


def hm_to_seconds(hhmm: str) -> int:
    """Parse a "HH:MM" clock string into seconds-past-midnight."""
    h, m = hhmm.split(":")
    return (int(h) * 60 + int(m)) * 60


@dataclass(frozen=True)
class Station:
    """A dog's feeding location: where to park, what to top up to, and (for the
    simulation) how much that dog eats and drinks per day."""

    name: str
    pose: Pose                    # where the robot parks to serve this bowl
    food_target_g: float          # top the food bowl *up to* this level
    water_target_ml: float        # top the water bowl *up to* this level
    food_capacity_g: float        # bowl physically holds no more than this
    water_capacity_ml: float
    dog_daily_food_g: float       # sim only: what the dog eats per day
    dog_daily_water_ml: float     # sim only: what the dog drinks per day

    def __post_init__(self) -> None:
        for v in (self.food_target_g, self.water_target_ml):
            if v < 0:
                raise ValueError(f"{self.name}: targets cannot be negative")
        if self.food_target_g > self.food_capacity_g:
            raise ValueError(f"{self.name}: food target exceeds bowl capacity")
        if self.water_target_ml > self.water_capacity_ml:
            raise ValueError(f"{self.name}: water target exceeds bowl capacity")


@dataclass(frozen=True)
class RobotConfig:
    """Physical limits and calibration of the machine itself."""

    hopper_capacity_g: float = 800.0       # onboard kibble tank (one round)
    tank_capacity_ml: float = 2000.0       # onboard water tank (one round)
    battery_capacity_wh: float = 100.0     # usable battery energy
    cruise_speed_mps: float = 0.25         # driving speed
    turn_speed_radps: float = 1.2          # rotation speed
    kibble_rate_gps: float = 15.0          # auger throughput (calibrated)
    water_rate_mlps: float = 40.0          # pump throughput (calibrated)
    # Power draw of each activity, in watts, for the battery model.
    drive_power_w: float = 20.0
    dispense_power_w: float = 8.0
    idle_power_w: float = 1.5
    # Closed-loop dosing tolerance: don't fuss below this, and the load cell is
    # accurate to roughly this band (used to size the "good enough" check).
    dose_tolerance_g: float = 3.0
    dose_tolerance_ml: float = 15.0


@dataclass(frozen=True)
class DockConfig:
    """The custom dock: bulk supplies + charger the robot returns to."""

    kibble_bin_capacity_g: float = 5000.0      # ~5 kg airtight bin (≈ 1 week)
    water_reservoir_capacity_ml: float = 19000.0  # ~5-gallon jug (≈ 1 week)
    charge_power_w: float = 60.0               # how fast the battery refills
    # Warn the owner to refill when bulk supplies drop below this fraction.
    low_supply_fraction: float = 0.15


@dataclass(frozen=True)
class HouseConfig:
    """The full picture: dock, stations, schedule, and the machine."""

    dock_pose: Pose
    stations: List[Station]
    feed_times: Tuple[str, ...] = ("07:00", "18:00")  # clock times per day
    robot: RobotConfig = field(default_factory=RobotConfig)
    dock: DockConfig = field(default_factory=DockConfig)

    def feed_seconds(self) -> List[int]:
        """Feed times as sorted seconds-past-midnight."""
        return sorted(hm_to_seconds(t) for t in self.feed_times)

    def worst_case_food_g(self) -> float:
        """Most kibble one round could need (every bowl bone dry)."""
        return sum(s.food_target_g for s in self.stations)

    def worst_case_water_ml(self) -> float:
        return sum(s.water_target_ml for s in self.stations)


def default_house() -> HouseConfig:
    """The two-dog home from the design brief.

    Coordinates are metres on a floor plan whose origin is the dock. Replace
    with a survey of the real house and the dogs' real portions.
    """
    return HouseConfig(
        dock_pose=Pose(0.0, 0.0, 0.0),
        stations=[
            Station(
                name="Rex",
                pose=Pose(4.0, 1.5, 0.0),
                food_target_g=250.0,
                water_target_ml=800.0,
                food_capacity_g=400.0,
                water_capacity_ml=1000.0,
                dog_daily_food_g=300.0,
                dog_daily_water_ml=1200.0,
            ),
            Station(
                name="Bella",
                pose=Pose(2.0, -3.0, 0.0),
                food_target_g=180.0,
                water_target_ml=700.0,
                food_capacity_g=300.0,
                water_capacity_ml=900.0,
                dog_daily_food_g=220.0,
                dog_daily_water_ml=1000.0,
            ),
        ],
    )
