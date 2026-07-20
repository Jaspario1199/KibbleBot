#!/usr/bin/env python3
"""Run a week of scheduled feeding rounds in simulation and print the report.

    python3 scripts/demo_sim.py

Two faults are staged to show the fail-safe behaviour:
  * Day 3 morning — Bella's bowl has been moved (vision can't find it) -> skip + alert
  * Day 5 evening — Rex's kibble auger jams -> food alert, water still delivered

No hardware, no network. Everything is deterministic for a given seed.
"""

from __future__ import annotations

import os
import sys

# Allow running as a plain script from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kibblebot.config import default_house           # noqa: E402
from kibblebot.mission import Telemetry               # noqa: E402
from kibblebot.scheduler import run_simulation        # noqa: E402
from kibblebot.simworld import SimWorld               # noqa: E402

DAYS = 7


def fmt_time(sec: float) -> str:
    day = int(sec // 86_400)
    rem = int(sec % 86_400)
    return f"D{day + 1} {rem // 3600:02d}:{(rem % 3600) // 60:02d}"


def stage_faults(day: int, index: int, world: SimWorld) -> None:
    if index == 4:                       # day 3 (0-indexed 2), morning round
        world.force_locate_fail["Bella"] = 2
    if index == 9:                       # day 5 (0-indexed 4), evening round
        world.force_kibble_jam.add("Rex")


def main() -> None:
    house = default_house()
    world = SimWorld(house, seed=7)
    tel = Telemetry()

    print("=" * 66)
    print(" kibble-bot — 7-day feeding simulation")
    print("=" * 66)
    print(f" Dogs      : {', '.join(s.name for s in house.stations)}")
    print(f" Schedule  : {', '.join(house.feed_times)} daily")
    print(f" Dock bin  : {house.dock.kibble_bin_capacity_g:.0f} g kibble, "
          f"{house.dock.water_reservoir_capacity_ml / 1000:.1f} L water")
    print("-" * 66)

    summary = run_simulation(house, world, DAYS, telemetry=tel, before_round=stage_faults)

    for r in summary.reports:
        badge = "OK " if r.success else "!! "
        parts = []
        for o in r.outcomes:
            if o.skipped:
                parts.append(f"{o.name}: SKIPPED ({o.note})")
            else:
                tag = "" if o.ok else f" [{o.note}]"
                parts.append(f"{o.name}: +{o.food_dispensed:.0f} g/+{o.water_dispensed:.0f} mL{tag}")
        print(f" {badge}{fmt_time(r.start_t):>9}  " + "   ".join(parts))

    print("-" * 66)
    print(f" Reliability      : {summary.reliability_pct:.0f}%  "
          f"({summary.rounds_successful}/{summary.rounds_total} rounds fully successful)")
    print(f" Dispensed        : {summary.total_food_g:.0f} g food, "
          f"{summary.total_water_ml / 1000:.2f} L water")
    print(f" Dock kibble left : {summary.dock_kibble_left_g:.0f} g "
          f"({100 * summary.dock_kibble_left_g / house.dock.kibble_bin_capacity_g:.0f}% after {DAYS} days)")
    print(f" Dock water left  : {summary.dock_water_left_ml / 1000:.2f} L "
          f"({100 * summary.dock_water_left_ml / house.dock.water_reservoir_capacity_ml:.0f}% after {DAYS} days)")
    print(f" Phone alerts     : {summary.alert_count}")

    if summary.telemetry and summary.telemetry.alerts:
        print("-" * 66)
        print(" 📱 Owner's phone (alerts):")
        for e in summary.telemetry.alerts:
            print(f"    {fmt_time(e.t):>9}  {e.message}")

    print("-" * 66)
    print(" Final bowl levels:")
    for s in house.stations:
        b = world.bowls[s.name]
        print(f"    {s.name:<6} food {b['food_g']:5.0f} g   water {b['water_ml']:6.0f} mL")
    print("=" * 66)


if __name__ == "__main__":
    main()
