"""Run many feeding rounds over many days and summarise how it went.

This is what turns a single ``run_round`` into a believable multi-day soak test:
between scheduled feeds the dogs eat and drink (``world.advance_to``), so each
round has real depletion to top back up, and the dock's bulk supplies draw down
day by day — which is how we check that a ~weekly refill actually lasts a week.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .config import HouseConfig
from .mission import FeedingMission, RoundReport, Telemetry
from .simworld import SimWorld

# A hook the demo/tests use to stage a fault right before a given round.
BeforeRound = Callable[[int, int, SimWorld], None]


@dataclass
class SimSummary:
    days: int
    reports: List[RoundReport] = field(default_factory=list)
    telemetry: Optional[Telemetry] = None
    dock_kibble_left_g: float = 0.0
    dock_water_left_ml: float = 0.0

    @property
    def rounds_total(self) -> int:
        return len(self.reports)

    @property
    def rounds_completed(self) -> int:
        return sum(1 for r in self.reports if r.completed)

    @property
    def rounds_successful(self) -> int:
        return sum(1 for r in self.reports if r.success)

    @property
    def reliability_pct(self) -> float:
        return 100.0 * self.rounds_successful / self.rounds_total if self.reports else 0.0

    @property
    def total_food_g(self) -> float:
        return sum(r.food_total for r in self.reports)

    @property
    def total_water_ml(self) -> float:
        return sum(r.water_total for r in self.reports)

    @property
    def alert_count(self) -> int:
        return len(self.telemetry.alerts) if self.telemetry else 0


def run_simulation(
    house: HouseConfig,
    world: SimWorld,
    days: int,
    telemetry: Optional[Telemetry] = None,
    before_round: Optional[BeforeRound] = None,
) -> SimSummary:
    tel = telemetry or Telemetry()
    mission = FeedingMission(world, house, tel)
    feed_secs = house.feed_seconds()

    reports: List[RoundReport] = []
    index = 0
    for day in range(days):
        for feed_idx, fs in enumerate(feed_secs):
            world.advance_to(day * 86_400 + fs)   # dogs eat/drink since last round
            if before_round is not None:
                before_round(day, index, world)
            reports.append(mission.run_round(index))
            index += 1

    return SimSummary(
        days=days,
        reports=reports,
        telemetry=tel,
        dock_kibble_left_g=world.dock_kibble_g,
        dock_water_left_ml=world.dock_water_ml,
    )
