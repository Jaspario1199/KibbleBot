import unittest

from kibblebot.config import default_house
from kibblebot.mission import FeedingMission, Telemetry
from kibblebot.scheduler import run_simulation
from kibblebot.simworld import SimWorld


class TestMission(unittest.TestCase):
    def setUp(self):
        self.house = default_house()
        self.world = SimWorld(self.house, seed=3)
        self.tel = Telemetry()
        self.mission = FeedingMission(self.world, self.house, self.tel)

    def test_nominal_round_tops_up_and_parks(self):
        report = self.mission.run_round(0)
        self.assertTrue(report.success)
        self.assertTrue(all(o.ok for o in report.outcomes))
        self.assertGreater(report.food_total, 0)
        self.assertGreater(report.water_total, 0)
        # Every bowl reached (about) its target.
        for s in self.house.stations:
            self.assertAlmostEqual(self.world.bowls[s.name]["food_g"], s.food_target_g, delta=3.0)
        # Robot ends parked on the dock.
        self.assertEqual(self.world.pose(), self.house.dock_pose)

    def test_bowl_not_found_is_skipped_with_alert(self):
        self.world.force_locate_fail["Rex"] = 2  # fail past the retry
        report = self.mission.run_round(0)
        self.assertFalse(report.success)
        self.assertTrue(report.completed)  # round still finished the other bowls
        rex = next(o for o in report.outcomes if o.name == "Rex")
        self.assertTrue(rex.skipped)
        self.assertTrue(self.tel.alerts)
        self.assertEqual(self.world.pose(), self.house.dock_pose)

    def test_pump_failure_alerts_but_food_still_served(self):
        self.world.force_pump_fail.add("Rex")
        report = self.mission.run_round(0)
        rex = next(o for o in report.outcomes if o.name == "Rex")
        self.assertFalse(rex.water_ok)
        self.assertTrue(rex.food_ok)
        self.assertGreater(rex.food_dispensed, 0)
        self.assertTrue(self.tel.alerts)

    def test_stuck_aborts_round_but_returns_to_dock(self):
        self.world.force_stuck = True
        report = self.mission.run_round(0)
        self.assertFalse(report.completed)
        self.assertIsNotNone(report.fault)
        self.assertEqual(self.world.pose(), self.house.dock_pose)  # failed safe


class TestScheduler(unittest.TestCase):
    def test_clean_multiday_run(self):
        house = default_house()
        world = SimWorld(house, seed=5)
        summary = run_simulation(house, world, days=2)
        self.assertEqual(summary.rounds_total, 4)          # 2 feeds x 2 days
        self.assertEqual(summary.reliability_pct, 100.0)   # no faults staged
        self.assertLess(summary.dock_kibble_left_g, house.dock.kibble_bin_capacity_g)
        self.assertGreater(summary.total_water_ml, 0)


if __name__ == "__main__":
    unittest.main()
