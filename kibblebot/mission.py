"""The feeding-round state machine and the telemetry/alerts it emits.

One ``run_round`` is one trip: reload at the dock, visit every station and top
its bowls up to target, then return and reload again for next time. Every branch
is written to *fail safe* — any fault the backend raises ends with the robot
parked at the dock and an alert queued for the owner's phone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from .backend import FeedingFault, RobotBackend
from .config import HouseConfig, Station


class State(str, Enum):
    PREFLIGHT = "preflight"
    TRANSIT = "transit"
    LOCATE = "locate"
    DISPENSE_FOOD = "dispense_food"
    DISPENSE_WATER = "dispense_water"
    RETURN = "return"
    REPORT = "report"
    FAULT = "fault"


@dataclass
class Event:
    t: float
    level: str      # "info" or "alert" (alerts are the phone notifications)
    state: State
    message: str


class Telemetry:
    """Collects the run's event log. ``alerts`` are what would ping the owner."""

    def __init__(self) -> None:
        self.events: List[Event] = []

    def info(self, t: float, state: State, message: str) -> None:
        self.events.append(Event(t, "info", state, message))

    def alert(self, t: float, state: State, message: str) -> None:
        self.events.append(Event(t, "alert", state, message))

    @property
    def alerts(self) -> List[Event]:
        return [e for e in self.events if e.level == "alert"]


@dataclass
class StationOutcome:
    name: str
    food_dispensed: float = 0.0
    water_dispensed: float = 0.0
    food_ok: bool = True
    water_ok: bool = True
    skipped: bool = False
    note: str = ""

    @property
    def ok(self) -> bool:
        return not self.skipped and self.food_ok and self.water_ok


@dataclass
class RoundReport:
    index: int
    start_t: float
    end_t: float
    outcomes: List[StationOutcome] = field(default_factory=list)
    fault: Optional[str] = None
    completed: bool = False

    @property
    def food_total(self) -> float:
        return sum(o.food_dispensed for o in self.outcomes)

    @property
    def water_total(self) -> float:
        return sum(o.water_dispensed for o in self.outcomes)

    @property
    def success(self) -> bool:
        return self.completed and self.fault is None and all(o.ok for o in self.outcomes)


class FeedingMission:
    def __init__(self, backend: RobotBackend, house: HouseConfig, telemetry: Telemetry):
        self.backend = backend
        self.house = house
        self.tel = telemetry

    def run_round(self, index: int = 0) -> RoundReport:
        b = self.backend
        report = RoundReport(index=index, start_t=b.now(), end_t=b.now())
        try:
            # PREFLIGHT — reload at the dock so every round starts full, then
            # check battery and warn on low bulk supplies.
            self.tel.info(b.now(), State.PREFLIGHT, "reloading + charging at dock")
            b.dock_and_reload()
            self._check_supplies()

            # Visit each station in order.
            for station in self.house.stations:
                report.outcomes.append(self._serve(station))

            # RETURN — home to the dock and reload for next time.
            self.tel.info(b.now(), State.RETURN, "returning to dock")
            b.drive_to(self.house.dock_pose)
            b.dock_and_reload()
            report.completed = True
        except FeedingFault as f:
            report.fault = str(f)
            self.tel.alert(b.now(), State.FAULT, f"round {index} aborted: {f}")
            self._safe_return()

        report.end_t = b.now()
        self._report(report)
        return report

    # -- states -------------------------------------------------------------

    def _serve(self, station: Station) -> StationOutcome:
        b = self.backend
        # TRANSIT — a STUCK fault here means we can't reach the bowl at all, so
        # it propagates up and aborts the whole round (fail safe).
        self.tel.info(b.now(), State.TRANSIT, f"driving to {station.name}")
        b.drive_to(station.pose)

        # LOCATE — one retry from a nudged heading before giving up.
        obs = b.locate_bowl(station)
        if not obs.found:
            self.tel.info(b.now(), State.LOCATE, f"{station.name}: bowl not found, retrying")
            b.drive_to(station.pose.with_heading(station.pose.theta + 0.35))
            obs = b.locate_bowl(station)
        if not obs.found:
            self.tel.alert(b.now(), State.LOCATE, f"{station.name}: bowl not found — skipped")
            return StationOutcome(station.name, skipped=True, note="bowl not found")

        outcome = StationOutcome(station.name)
        notes: List[str] = []

        # DISPENSE FOOD
        try:
            res = b.dispense_kibble(station, station.food_target_g, obs.food_g)
            outcome.food_dispensed = res.dispensed
            if res.capped:
                outcome.food_ok = False
                notes.append("food short (hopper low)")
                self.tel.alert(b.now(), State.DISPENSE_FOOD, f"{station.name}: food short, hopper low")
            else:
                self.tel.info(b.now(), State.DISPENSE_FOOD, f"{station.name}: +{res.dispensed:.0f} g food")
        except FeedingFault as f:
            outcome.food_ok = False
            notes.append(f"food fault: {f.fault.value}")
            self.tel.alert(b.now(), State.DISPENSE_FOOD, f"{station.name}: {f}")

        # DISPENSE WATER
        try:
            res = b.dispense_water(station, station.water_target_ml, obs.water_ml)
            outcome.water_dispensed = res.dispensed
            if res.capped:
                outcome.water_ok = False
                notes.append("water short (tank low)")
                self.tel.alert(b.now(), State.DISPENSE_WATER, f"{station.name}: water short, tank low")
            else:
                self.tel.info(b.now(), State.DISPENSE_WATER, f"{station.name}: +{res.dispensed:.0f} mL water")
        except FeedingFault as f:
            outcome.water_ok = False
            notes.append(f"water fault: {f.fault.value}")
            self.tel.alert(b.now(), State.DISPENSE_WATER, f"{station.name}: {f}")

        outcome.note = "; ".join(notes)
        return outcome

    # -- helpers ------------------------------------------------------------

    def _check_supplies(self) -> None:
        b = self.backend
        lv = b.levels()
        d = self.house.dock
        if lv.dock_kibble_g < d.low_supply_fraction * d.kibble_bin_capacity_g:
            self.tel.alert(b.now(), State.PREFLIGHT,
                           f"kibble bin low ({lv.dock_kibble_g:.0f} g) — refill soon")
        if lv.dock_water_ml < d.low_supply_fraction * d.water_reservoir_capacity_ml:
            self.tel.alert(b.now(), State.PREFLIGHT,
                           f"water reservoir low ({lv.dock_water_ml:.0f} mL) — refill soon")

    def _safe_return(self) -> None:
        """Best-effort: get the robot back on the dock after any abort."""
        b = self.backend
        try:
            b.drive_to(self.house.dock_pose)
            b.dock_and_reload()
            self.tel.info(b.now(), State.FAULT, "parked safely at dock")
        except FeedingFault as f:
            self.tel.alert(b.now(), State.FAULT, f"could not return to dock: {f}")

    def _report(self, report: RoundReport) -> None:
        b = self.backend
        if report.success:
            self.tel.info(b.now(), State.REPORT,
                          f"round {report.index} complete: "
                          f"{report.food_total:.0f} g food, {report.water_total:.0f} mL water")
        else:
            issues = [o.name for o in report.outcomes if not o.ok]
            detail = report.fault or ("issues at " + ", ".join(issues) if issues else "incomplete")
            self.tel.alert(b.now(), State.REPORT, f"round {report.index} needs attention: {detail}")
