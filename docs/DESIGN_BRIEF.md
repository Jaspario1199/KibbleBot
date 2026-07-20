# kibble-bot — Design Brief (living document)

> Status: **DRAFT / groundwork.** This is the shared source of truth for *what*
> we're building and *why*, agreed before any CAD or firmware. Numbers marked
> **(TBD)** need a decision. Nothing here is committed to hardware yet.

## 1. Vision

An autonomous robot that keeps two dogs fed and watered while their owner is
away and the household can't manage feeding. A **custom dock** in the food/water
room stores bulk kibble and water and **auto-reloads the robot**. On a schedule,
the robot leaves the dock, drives to the dogs' bowls, **tops them up to a
target** amount, and returns to reload and recharge.

## 2. Operating model (owner's words)

> "A robot docked in the room with the food and water in a custom dock we build.
> The dock does auto-top-ups on the robot. Then at certain scheduled times, the
> robot goes out, finds the water and food bowls, fills them, and goes back."

## 3. Design principles

1. **Welfare-critical, so fail safe.** Any fault → retreat to the dock and alert
   the owner's phone. The robot never does something worse than doing nothing.
2. **Never overfill.** Sense the bowl and dispense only the *delta* up to target;
   a full bowl (dog didn't eat) is a signal, not a reason to pile on more.
3. **Cleanability is a v1 requirement**, not polish. If a cleaning task is
   annoying, it won't happen and the machine will fail on hygiene.
4. **Closed-loop dosing.** Weigh what's dispensed; don't trust "run motor N secs".
5. **Config-driven.** The house map, portions, and schedule are data, not code.

## 4. Scope

**In (v1)**
- One floor; a small number of fixed bowl/station locations.
- Top up food & water to a target; never overfill.
- Custom dock: recharge + auto-reload kibble & water.
- Scheduled rounds; remote status + fault alerts.

**Out (later)**
- Stairs / multiple floors (wheeled robot can't climb — stairs are no-go zones).
- Knowing *which* dog eats/drinks.
- Washing or moving bowls.
- Plumbed-in water.

**Non-goals**
- Being the sole/last-resort water source if that risks the dogs. (Owner opted
  for the roaming model; we mitigate with fail-safe + alerts, and can add a
  simple always-on backup waterer later if desired.)

## 5. The dogs & the house (known)

- **2 dogs, small–medium** (planning envelope ≈ up to 25 kg each).
- **All bowls on one level.** Stairs treated as no-go via cliff sensors.
- **Weekly human refill** of the dock's bulk food/water is available.

## 6. Capacity math (planning envelope — refine with real portions)

Conservative daily needs for 2 small–medium dogs:

| Resource | Per dog/day | 2 dogs/day | + margin (plan) | 7-day dock reservoir |
|---|---|---|---|---|
| Kibble | ~200–300 g | ~500 g | **~700 g/day** | **~5 kg bin** |
| Water (drink+evap) | ~1–1.25 L | ~2.5 L | **~3 L/day** | **~20 L (≈ 5-gal jug)** |

- A **5 kg airtight kibble bin** and a **~5-gallon water jug** at the dock line
  up almost exactly with a **weekly refill** — good fit.
- **Robot onboard tanks** only need to survive one round (dock reloads after):
  **hopper ≈ 0.5–0.8 kg**, **water tank ≈ 1.5–2 L**.
- **Battery:** a round is a short drive + dispense; energy per round is small.
  Size for many rounds + margin, recharge at dock. Not a binding constraint on
  one level.

## 7. Feeding workflow (day in the life)

1. **Schedule fires.** **Food + water together, 2×/day** (morning + evening).
   Each round tops up both bowls to target. (Kept simple by owner's choice;
   the scheduler is configurable if we later want extra water-only rounds.)
2. **Pre-flight:** enough kibble + water + battery for the round *plus reserve*?
   If not → reload/charge at dock first, or alert.
3. **Undock** → for each station: navigate → align to bowl → **sense current
   level** → dispense only the delta up to target → **verify by weight** → log.
4. **Return to dock** → recharge → auto-reload hopper/tank from bulk reservoir.
5. **Report** the round to the owner's phone; sleep until next trigger.
6. **Fail safe:** stuck / bowl not found / jam / low battery mid-round → retreat
   to dock + alert.

## 8. The custom dock

- **Alignment:** IR beacon or fiducial (AprilTag) so the robot self-parks, like a
  vacuum dock.
- **Charging:** sprung pogo/contact pads mate on arrival.
- **Kibble reload:** gravity chute from the bulk bin → robot hopper, gated by a
  servo/auger; stop when the robot's load cell reads "full."
- **Water reload:** dock reservoir → robot tank via a self-sealing quick-connect
  or a spout + valve; float/level sensor stops the fill.
- **Hygiene at the dock:** opaque (anti-algae) drainable water jug; robot tank
  fills fresh per round and can run near-empty between rounds to avoid standing
  water. The dock is the "clean base station."

## 9. Perception & bowl delivery *(DECIDED: AI camera recognition)*

The robot **tops up the dogs' existing bowls in place**, locating and aligning to
them with **AI camera recognition** (owner's choice) rather than fiducial-marked
stations.

- **Approach:** an onboard camera runs an object detector trained/fine-tuned to
  recognize the **food bowl** and **water bowl**. Coarse waypoint nav gets the
  robot to the room; **vision homing** aligns the dispense nozzle over the bowl
  for the final approach; a depth/ToF sensor confirms range and bowl fill level.
- **Reliability guards (because vision is fuzzy):** confidence threshold + retry
  from a new angle; if the bowl can't be confidently found (moved, occluded, a dog
  standing over it) → skip that station, log, and alert rather than dumping food on
  the floor. Optional cheap fallback: a distinct color/marker on each bowl to make
  detection rock-solid.
- **Cleanliness compromise (no fiducial needed):** sit each bowl on a **wipeable
  spill tray**. Keeps the AI-recognition workflow but contains crumbs/splashes and
  makes cleanup a 10-second wipe.
- **Training data:** capture photos of *these* bowls in *this* room under day/night
  lighting; fine-tune a small detector (e.g. a YOLO-class model) on-device or on a
  laptop. (Detailed in the vision plan once we start Phase 1.)

## 10. Hygiene & maintenance (make-or-break)

- **Water:** food-grade silicone tubing + **peristaltic pump** (only the tube
  touches water), removable dishwasher-safe tank, **air-gap nozzle** (never dips
  into the bowl → no backflow/biofilm transfer), periodic flush + drain-dry.
- **Kibble:** sealed gasketed hopper, smooth food-safe surfaces (HDPE/PETG),
  **removable auger** for cleaning, keep dry (humidity clumps kibble & jams augers).
- **The house:** sealed electronics (dog hair kills fans), IP-rated splash zone on
  the water side, wipeable exterior, zero spillage (kibble crumbs = ants),
  hair-resistant wheels (no tangle-prone brushes).
- **Maintenance cadence (a design input):** daily remote glance (camera), weekly
  tank flush + hopper wipe + bowl wash, monthly tubing deep-clean, periodic tubing
  replacement.

## 11. Materials / BOM — initial instincts *(not final)*

- **Mobile base: scratch-built, purpose-designed** — low & wide with the water
  tank between the wheels for stability; full motor control; camera nav + dock
  homing. (Chosen over a vacuum base: on one fixed floor with AI vision we don't
  need whole-house SLAM, and a vacuum handles a ~2 L water payload poorly.)
  - 2× 12 V gearmotors **with encoders** + wheels · motor driver · caster.
  - 3× IR **cliff sensors** (stairs), ToF/ultrasonic obstacle, IMU.
- **Kibble dispense:** stepper-driven auger + **HX711 load cell** (closed-loop g).
- **Water dispense:** food-grade **peristaltic pump**, dispense by weight/flow.
- **Compute:** Raspberry Pi (vision/nav) + **ESP32** (real-time motor & dispensing).
- **Sensors:** camera (+ AprilTags at stations), ToF/obstacle, **cliff sensors**,
  IMU, load cells, water-level, battery gauge.
- **Dock:** charging contacts + gravity kibble chute + water reservoir + fiducial.
- **Power:** LiFePO₄ or Li-ion, recharged at dock.
- **Connectivity:** Wi-Fi for status + alerts (required — owner is remote).

## 12. Metrics & success criteria

- **Feeding reliability:** ≥ 99% of scheduled rounds completed.
- **Dosing accuracy:** kibble ±5–10 g; water ±25 mL (closed-loop).
- **Endurance:** ≥ 7 days unattended per human refill; many rounds per charge.
- **Docking success rate**; **collisions per 100 rounds**.
- **Alert latency:** owner notified of a fault in < a few minutes.
- **Zero-tolerance:** no overfeed events; no water-into-electronics faults; no dog
  able to tip or open it.

**Success looks like:** *Owner away two weeks. Twice a day the robot tops both
bowls to target and returns to charge, sending a "✅ fed, tanks 60%" ping. Low
tank → "please refill me." A fault → alert, and the robot safely parked.*

## 13. Risks & open decisions

- **[DECIDED] Budget:** **$300–700** — vacuum-or-scratch base + Pi/ESP32 + load
  cell + peristaltic pump, with room for spares.
- **[DECIDED] Delivery:** **existing bowls + AI camera recognition** (see §9),
  with wipeable spill trays.
- **[DECIDED] Schedule:** **food + water together, 2×/day.**
- **[DECIDED] Base: scratch-built purpose design** (low/wide, stable water
  payload, camera nav + dock homing). See §11.
- **[RISK] Vision reliability.** Lighting/occlusion/moved bowls → confidence
  threshold, retry, skip-and-alert; optional bowl color-markers as a fallback.
- **[RISK] Water + electronics + dogs.** Splash zones, air gaps, sealed compute.
- **[RISK] Overfeeding / a dog that isn't eating.** Sense-before-dispense + report.
- **[RISK] Robot as a chew toy / tip hazard.** Ruggedize, hide cables, weight low.
- **[RISK] Sole dependency.** Fail-safe + alerts; optional simple backup waterer.

## 14. Rough roadmap (phases)

0. **Groundwork** (this doc) — lock scope, metrics, decisions above.
1. **Simulate the mission** end-to-end in software (no hardware): config, nav,
   dispensing model, dock reload, schedule, fault handling.
2. **Bench dispensing rigs** — auger + load cell (grams), pump + air-gap (mL) — on
   the desk, closed-loop, no chassis.
3. **Mobile base + dock** — driving, self-docking, recharge + reload.
4. **Integration** — full scheduled rounds in the real room.
5. **Hardening** — hygiene cycles, alerts, endurance, week-long soak test.
