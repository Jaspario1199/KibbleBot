import math
import unittest

from kibblebot.geometry import Pose, wrap_angle


class TestGeometry(unittest.TestCase):
    def test_distance(self):
        self.assertAlmostEqual(Pose(0, 0).distance_to(Pose(3, 4)), 5.0)

    def test_bearing_east_and_north(self):
        self.assertAlmostEqual(Pose(0, 0).bearing_to(Pose(1, 0)), 0.0)
        self.assertAlmostEqual(Pose(0, 0).bearing_to(Pose(0, 1)), math.pi / 2)

    def test_heading_error_is_signed_and_bounded(self):
        # Facing +x, target due north -> a +90 degree turn.
        self.assertAlmostEqual(Pose(0, 0, 0.0).heading_error_to(Pose(0, 1)), math.pi / 2)
        # Any heading error stays within (-pi, pi].
        err = Pose(0, 0, -math.pi + 0.1).heading_error_to(Pose(-1, 0))
        self.assertLessEqual(abs(err), math.pi + 1e-9)

    def test_wrap_angle(self):
        self.assertAlmostEqual(wrap_angle(3 * math.pi), math.pi)
        self.assertAlmostEqual(wrap_angle(0.0), 0.0)


if __name__ == "__main__":
    unittest.main()
