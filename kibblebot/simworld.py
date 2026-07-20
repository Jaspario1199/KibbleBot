"""A physics-lite simulation of the whole world: the robot, the bowls, the dock,
and the dogs eating/drinking between rounds.

``SimWorld`` implements :class:`~kibblebot.backend.RobotBackend`, so the mission
drives it exactly as it would drive real hardware. It also exposes a couple of
sim-only helpers (``advance_to``, fault-injection sets) that the scheduler and
tests use to move time forward and to stage failures deterministically.

Determinism: all randomness comes from a seeded ``random.Random``; with the same
seed and no injected faults, a run is fully reproducible.
"""

from __future__ import annotations

import random
from typing import Dict, Set  # noqa: F401  (Set used by other injection points)

from .backend import (
    BowlObservation,
    DispenseResult,
    FaultType,
    FeedingFault,
    ResourceLevels,
    RobotBackend,
)
from .config import HouseConfig, Station
from .dispensing import compute_dose
from .geometry import Pose

SECONDS_PER_DAY = 86_400


class SimWorld(RobotBackend):
    def __init__(
        self,
        house: HouseConfig,
        seed: int = 0,
        sensing_noise_g: float = 2.0,
        sensing_noise_ml: float = 8.0,
        start_bowls_empty: bool = True,
    ):
        self.house = house
        self.rng = random.Random(seed)
        self.t = 0.0

        r = house.robot
        d = house.dock
        # The robot starts docked, freshly reloaded and charged.
        self._pose = house.dock_pose
        self.kibble_g = r.hopper_capacity_g
        self.water_ml = r.tank_capacity_ml
        self.battery_wh = r.battery_capacity_wh
        # Bulk supplies start full (someone just did the weekly refill).
        self.dock_kibble_g = d.kibble_bin_capacity_g
        self.dock_water_ml = d.water_reservoir_capacity_ml

        self.bowls: Dict[str, Dict[str, float]] = {}
        for s in house.stations:
            if start_bowls_empty:
                self.bowls[s.name] = {"food_g": 0.0, "water_ml": 0.0}
            else:
                self.bowls[s.name] = {"food_g": s.food_target_g, "water_ml": s.water_target_ml}

        self.sensing_noise_g = sensing_noise_g
        self.sensing_noise_ml = sensing_noise_ml

        # Deterministic fault injection. ``force_locate_fail`` maps a station to
        # how many *consecutive* locate attempts should fail (2 = fail past the
        # retry, so the station is skipped). The others are one-shot: add a
        # station name and the next matching action fails once, then clears.
        self.force_locate_fail: Dict[str, int] = {}
        self.force_kibble_jam: Set[str] = set()
        self.force_pump_fail: Set[str] = set()
        self.force_stuck: bool = False
        self.force_dock_fail: bool = False

    # -- internal helpers ---------------------------------------------------

    def _spend(self, power_w: float, seconds: float) -> None:
        """Advance the clock and drain the battery for an activity."""
        self.battery_wh = max(0.0, self.battery_wh - power_w * seconds / 3600.0)
        self.t += seconds

    # -- RobotBackend -------------------------------------------------------

    def now(self) -> float:
        return self.t

    def pose(self) -> Pose:
        return self._pose

    def drive_to(self, target: Pose) -> float:
        r = self.house.robot
        dist = self._pose.distance_to(target)
        turn = abs(self._pose.heading_error_to(target)) if dist > 1e-6 else 0.0
        travel_time = dist / r.cruise_speed_mps + turn / r.turn_speed_radps
        if self.force_stuck:
            self.force_stuck = False
            self._spend(r.drive_power_w, travel_time * 0.5)  # wedged partway
            raise FeedingFault(FaultType.STUCK, "wheels wedged en route")
        self._spend(r.drive_power_w, travel_time)
        self._pose = target
        return travel_time

    def locate_bowl(self, station: Station) -> BowlObservation:
        self._spend(self.house.robot.idle_power_w, 2.0)  # look/align time
        remaining = self.force_locate_fail.get(station.name, 0)
        if remaining > 0:
            if remaining <= 1:
                self.force_locate_fail.pop(station.name, None)
            else:
                self.force_locate_fail[station.name] = remaining - 1
            return BowlObservation(found=False)
        b = self.bowls[station.name]
        food = max(0.0, b["food_g"] + self.rng.uniform(-self.sensing_noise_g, self.sensing_noise_g))
        water = max(0.0, b["water_ml"] + self.rng.uniform(-self.sensing_noise_ml, self.sensing_noise_ml))
        return BowlObservation(found=True, food_g=food, water_ml=water)

    def dispense_kibble(self, station: Station, target_g: float, current_g: float) -> DispenseResult:
        r = self.house.robot
        if station.name in self.force_kibble_jam:
            self.force_kibble_jam.discard(station.name)
            raise FeedingFault(FaultType.KIBBLE_JAM, "auger jammed", station.name)
        ceiling = min(target_g, station.food_capacity_g)
        dose = compute_dose(current_g, target_g, station.food_capacity_g, self.kibble_g, r.dose_tolerance_g)
        if dose > 0:
            self._spend(r.dispense_power_w, dose / r.kibble_rate_gps)
            self.kibble_g -= dose
            self.bowls[station.name]["food_g"] += dose
        capped = (ceiling - current_g - dose) > r.dose_tolerance_g
        return DispenseResult(dose, self.bowls[station.name]["food_g"], capped)

    def dispense_water(self, station: Station, target_ml: float, current_ml: float) -> DispenseResult:
        r = self.house.robot
        if station.name in self.force_pump_fail:
            self.force_pump_fail.discard(station.name)
            raise FeedingFault(FaultType.PUMP_FAIL, "pump air-locked", station.name)
        ceiling = min(target_ml, station.water_capacity_ml)
        dose = compute_dose(current_ml, target_ml, station.water_capacity_ml, self.water_ml, r.dose_tolerance_ml)
        if dose > 0:
            self._spend(r.dispense_power_w, dose / r.water_rate_mlps)
            self.water_ml -= dose
            self.bowls[station.name]["water_ml"] += dose
        capped = (ceiling - current_ml - dose) > r.dose_tolerance_ml
        return DispenseResult(dose, self.bowls[station.name]["water_ml"], capped)

    def dock_and_reload(self) -> None:
        r = self.house.robot
        d = self.house.dock
        if self.force_dock_fail:
            self.force_dock_fail = False
            raise FeedingFault(FaultType.DOCK_FAILED, "missed dock contacts")
        self._pose = self.house.dock_pose
        # Reload kibble and water from the bulk supplies (as available).
        take_k = min(r.hopper_capacity_g - self.kibble_g, self.dock_kibble_g)
        self.kibble_g += take_k
        self.dock_kibble_g -= take_k
        take_w = min(r.tank_capacity_ml - self.water_ml, self.dock_water_ml)
        self.water_ml += take_w
        self.dock_water_ml -= take_w
        # Recharge to full.
        deficit_wh = r.battery_capacity_wh - self.battery_wh
        if d.charge_power_w > 0:
            self.t += deficit_wh / d.charge_power_w * 3600.0
        self.battery_wh = r.battery_capacity_wh
        self.t += 20.0  # mechanical reload time

    def levels(self) -> ResourceLevels:
        r = self.house.robot
        return ResourceLevels(
            onboard_kibble_g=self.kibble_g,
            onboard_water_ml=self.water_ml,
            battery_pct=100.0 * self.battery_wh / r.battery_capacity_wh,
            dock_kibble_g=self.dock_kibble_g,
            dock_water_ml=self.dock_water_ml,
        )

    # -- sim-only ------------------------------------------------------------

    def advance_to(self, t_target: float) -> None:
        """Move the clock forward to ``t_target``, letting the dogs eat/drink.

        The robot is parked and charging between rounds, so the battery is not
        drained here — only the bowls deplete.
        """
        dt = t_target - self.t
        if dt <= 0:
            return
        for s in self.house.stations:
            b = self.bowls[s.name]
            b["food_g"] = max(0.0, b["food_g"] - s.dog_daily_food_g * dt / SECONDS_PER_DAY)
            b["water_ml"] = max(0.0, b["water_ml"] - s.dog_daily_water_ml * dt / SECONDS_PER_DAY)
        self.t = t_target
