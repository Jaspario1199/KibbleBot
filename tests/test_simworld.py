import unittest

from kibblebot.backend import FeedingFault
from kibblebot.config import default_house
from kibblebot.geometry import Pose
from kibblebot.simworld import SimWorld


class TestSimWorld(unittest.TestCase):
    def setUp(self):
        self.house = default_house()
        self.world = SimWorld(self.house, seed=1)
        self.rex = self.house.stations[0]

    def test_starts_full_and_docked(self):
        lv = self.world.levels()
        self.assertEqual(lv.onboard_kibble_g, self.house.robot.hopper_capacity_g)
        self.assertEqual(lv.onboard_water_ml, self.house.robot.tank_capacity_ml)
        self.assertEqual(lv.battery_pct, 100.0)
        self.assertEqual(self.world.pose(), self.house.dock_pose)

    def test_drive_moves_and_drains_battery(self):
        t0 = self.world.now()
        self.world.drive_to(Pose(4.0, 0.0))
        self.assertEqual(self.world.pose().x, 4.0)
        self.assertGreater(self.world.now(), t0)
        self.assertLess(self.world.levels().battery_pct, 100.0)

    def test_dispense_never_overfills(self):
        self.world.bowls["Rex"]["food_g"] = 0.0
        res = self.world.dispense_kibble(self.rex, self.rex.food_target_g, 0.0)
        self.assertLessEqual(res.bowl_after, self.rex.food_capacity_g)
        self.assertAlmostEqual(res.bowl_after, self.rex.food_target_g, delta=1.0)
        # A second dispense at target adds nothing.
        res2 = self.world.dispense_kibble(self.rex, self.rex.food_target_g, res.bowl_after)
        self.assertEqual(res2.dispensed, 0.0)

    def test_dispense_decrements_onboard(self):
        before = self.world.kibble_g
        res = self.world.dispense_kibble(self.rex, self.rex.food_target_g, 0.0)
        self.assertAlmostEqual(self.world.kibble_g, before - res.dispensed)

    def test_dogs_consume_between_rounds(self):
        self.world.bowls["Rex"]["food_g"] = 250.0
        self.world.advance_to(43_200)  # half a day
        self.assertAlmostEqual(self.world.bowls["Rex"]["food_g"],
                               250.0 - self.rex.dog_daily_food_g / 2, delta=0.5)

    def test_dock_reload_refills_from_bulk(self):
        self.world.kibble_g = 100.0
        dock_before = self.world.dock_kibble_g
        self.world.dock_and_reload()
        self.assertEqual(self.world.kibble_g, self.house.robot.hopper_capacity_g)
        self.assertLess(self.world.dock_kibble_g, dock_before)

    def test_locate_fail_injection_then_recovers(self):
        self.world.force_locate_fail["Rex"] = 1
        self.assertFalse(self.world.locate_bowl(self.rex).found)
        self.assertTrue(self.world.locate_bowl(self.rex).found)

    def test_jam_injection_raises(self):
        self.world.force_kibble_jam.add("Rex")
        with self.assertRaises(FeedingFault):
            self.world.dispense_kibble(self.rex, self.rex.food_target_g, 0.0)


if __name__ == "__main__":
    unittest.main()
