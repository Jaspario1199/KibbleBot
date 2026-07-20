# Phase 1 — Mission Simulator

Phase 1 proves the *whole feeding mission in software*, with no hardware and no
network. It exists to answer the questions that are expensive to get wrong on a
real robot around real dogs:

- Does the round logic (reload → drive → find bowl → dose → return) hold together?
- Can we **guarantee we never overfill a bowl**?
- Do faults (bowl moved, auger jam, pump fail, wheels stuck) actually **fail
  safe** — robot back on the dock, owner alerted?
- Are the **portions, schedule, and dock sizing** right? Does a ~5 kg bin + ~5-gal
  jug really last a week?

## Run it

```bash
# the full 7-day simulation with a readable report
python3 scripts/demo_sim.py

# the test suite (stdlib only, no pytest needed)
python3 -m unittest discover -s tests -t .
```

## How it's built

Everything is driven through one interface, so the logic proven here moves onto
the real robot unchanged.

```
          FeedingMission (the state machine)
                     │  drives
                     ▼
             RobotBackend  (interface: backend.py)
                     ▲  implemented by
                     │
   SimWorld (sim today)   ─┄┄►   real MCU backend (Phase 3)
```

| Module | Responsibility |
|---|---|
| `config.py` | The house, dogs, targets, schedule, robot + dock specs (all data) |
| `geometry.py` | 2D pose/vector math (stdlib only) |
| `backend.py` | The `RobotBackend` interface + result/fault types |
| `dispensing.py` | The **never-overfill** dosing math (pure functions) |
| `simworld.py` | Physics-lite backend; also models dogs eating between rounds |
| `mission.py` | The feeding-round state machine + telemetry / phone alerts |
| `scheduler.py` | Runs many rounds over many days, summarises reliability |

## The mission, state by state

`PREFLIGHT` (reload + charge at dock) → for each station: `TRANSIT` → `LOCATE`
(one retry, else skip + alert) → `DISPENSE_FOOD` → `DISPENSE_WATER` → `RETURN`
(dock + reload). Any `FeedingFault` the backend raises unwinds to `FAULT`, which
best-effort returns the robot to the dock and queues an alert.

## What the demo shows

A 7-day run of the two-dog house with two faults staged in:

- **Day 3 morning** — Bella's bowl has been moved; vision can't find it after a
  retry → **skipped, owner alerted**, and it recovers on the next round.
- **Day 5 evening** — Rex's kibble auger jams → **food alert, water still
  delivered**, food recovers next round.

Representative output:

```
 Reliability      : 86%  (12/14 rounds fully successful)
 Dispensed        : 3686 g food, 15.36 L water
 Dock kibble left : 1314 g (26% after 7 days)
 Dock water left  : 3.64 L (19% after 7 days)
 Phone alerts     : 4
```

The 26% / 19% remaining after a week is the number that **validates the weekly
refill + dock sizing** from the design brief. (The two "failures" are the staged
faults; with none injected the scheduler reports 100%.)

## Design guarantees exercised by the tests

- `compute_dose` never exceeds the target, the bowl capacity, or what's onboard,
  and dispenses **nothing** into an already-full bowl.
- A nominal round tops every bowl to target (±tolerance) and ends **docked**.
- Bowl-not-found → station skipped, round still completes, **alert raised**.
- Pump failure → water alert, **food still served**.
- Wheels stuck → round aborts but the robot **returns to the dock** (fail safe).

## Deliberately deferred (later phases)

- Real vision (the AI bowl detector) — here `locate_bowl` is modelled.
- Real navigation/SLAM — here driving is straight-line time + battery cost.
- Real dispensing hardware (auger + load cell, pump + air gap) — Phase 2 bench rigs.
- Real alerts (push notification) — here they're collected in `Telemetry`.
