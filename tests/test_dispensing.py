import unittest

from kibblebot.dispensing import compute_dose


class TestComputeDose(unittest.TestCase):
    def test_normal_topup(self):
        self.assertAlmostEqual(compute_dose(100, 250, 400, 800), 150)

    def test_already_at_target_dispenses_nothing(self):
        self.assertEqual(compute_dose(250, 250, 400, 800), 0.0)

    def test_above_target_dispenses_nothing(self):
        # Dog didn't eat; a full bowl must never be topped up further.
        self.assertEqual(compute_dose(300, 250, 400, 800), 0.0)

    def test_never_exceeds_bowl_capacity(self):
        # Target above capacity -> capped at capacity's remaining room.
        self.assertAlmostEqual(compute_dose(100, 500, 300, 800), 200)

    def test_never_exceeds_onboard_supply(self):
        self.assertAlmostEqual(compute_dose(0, 250, 400, 50), 50)

    def test_tolerance_suppresses_dribbles(self):
        self.assertEqual(compute_dose(249, 250, 400, 800, tolerance=3), 0.0)

    def test_negative_inputs_rejected(self):
        with self.assertRaises(ValueError):
            compute_dose(-1, 250, 400, 800)


if __name__ == "__main__":
    unittest.main()
