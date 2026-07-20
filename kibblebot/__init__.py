"""kibble-bot: an autonomous dog feeding + watering robot.

Phase 1 is a pure-software simulation of the whole feeding mission so the
control logic can be proven and the portions/schedule tuned on a laptop, long
before any hardware exists. The pieces:

    geometry     - 2D pose / vector math (stdlib only)
    config       - the house map, feeding targets, schedule, robot + dock specs
    backend      - the RobotBackend interface the mission drives, plus the
                   shared result/fault types
    dispensing   - the "never overfill" dosing math (pure functions)
    simworld     - a physics-lite backend that implements RobotBackend and also
                   models the dogs eating/drinking between rounds
    mission      - the feeding-round state machine + telemetry / phone alerts
    scheduler    - runs many rounds over many days and reports the outcome

Because the simulator and the (future) real robot both satisfy the same
``RobotBackend`` interface, the mission logic written and tested here moves onto
the real machine unchanged.
"""

__version__ = "0.1.0"
