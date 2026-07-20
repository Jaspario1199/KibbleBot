# 🐾 kibble-bot

An autonomous robot that keeps two dogs fed and watered while their owner is
away. A **custom dock** stores bulk kibble and water and auto-reloads the robot;
on a schedule the robot drives out, tops up the dogs' bowls using **AI camera
recognition**, and returns to recharge and reload.

> **Status: Phase 1 (software simulation).** Groundwork is locked in
> **[`docs/DESIGN_BRIEF.md`](docs/DESIGN_BRIEF.md)**; the whole feeding mission
> now runs in simulation — no hardware yet. See **[`docs/PHASE1.md`](docs/PHASE1.md)**.

## The idea in one loop

```
  ┌─ dock (bulk kibble + water + charger) ─┐
  │                                        │
  scheduled time → undock → drive to bowls → find bowl (AI camera)
  → top up food + water (never overfill, weigh what's dispensed)
  → return to dock → recharge + reload → ping owner "✅ fed"
  │                                        │
  └──────── fail safe: any fault → park at dock + alert ───────┘
```

## What's decided (see the brief for the why)

- **Roaming robot + custom reloading dock**, fail-safe with phone alerts.
- **2 small–medium dogs, one floor**, weekly human refill of the dock.
- **Scratch-built base** — low & wide, water tank between the wheels for stability.
- **AI camera recognition** to find/align to the dogs' existing bowls (+ spill trays).
- **Food + water together, 2×/day.**
- **Budget $300–700**; ~5 kg kibble bin + ~5-gal water jug at the dock ≈ 7 days.

## Try the simulation (Phase 1)

No hardware or install needed — the simulator is pure Python standard library:

```bash
python3 scripts/demo_sim.py                       # a 7-day feeding run + report
python3 -m unittest discover -s tests -t .         # the test suite (24 tests)
```

The demo runs a full week for the two-dog house, stages a couple of faults
(a moved bowl, a jammed auger), and prints reliability, how much was dispensed,
the owner's alert feed, and how much dock supply is left after 7 days — the
number that validates the weekly-refill sizing. Details in
**[`docs/PHASE1.md`](docs/PHASE1.md)**.

## Design principles

1. **Welfare-critical → fail safe.** Any fault: retreat to dock, alert the owner.
2. **Never overfill.** Sense the bowl, dispense only the delta, weigh the result.
3. **Cleanability is a v1 requirement**, not polish.
4. **Config-driven** — house map, portions, and schedule are data, not code.

## Roadmap

0. **Groundwork** — scope, metrics, decisions ✅
1. **Simulate the mission** end-to-end in software (no hardware) ✅
2. **Bench dispensing rigs** — auger + load cell, pump + air-gap ← next
3. **Mobile base + dock** — driving, self-docking, recharge + reload
4. **Integration** — full scheduled rounds in the real room
5. **Hardening** — hygiene cycles, alerts, endurance, week-long soak test

See **[`docs/DESIGN_BRIEF.md`](docs/DESIGN_BRIEF.md)** for scope, capacity math,
BOM, hygiene plan, metrics, and open risks.
