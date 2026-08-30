import unittest

from robot_hat import MockIMU
from robot_hat.exceptions import IMUInitializationError, IMUReadError


class TestMockIMU(unittest.TestCase):
    def test_stationary_defaults_and_mutable_sample(self) -> None:
        imu = MockIMU(monotonic_ns=iter((10, 20)).__next__)
        imu.initialize()

        first = imu.read_sample()
        self.assertEqual(first.acceleration_mps2, (0.0, 0.0, 9.80665))
        self.assertEqual(first.angular_velocity_radps, (0.0, 0.0, 0.0))
        self.assertEqual(first.timestamp_monotonic_ns, 10)

        imu.set_sample(
            acceleration_mps2=(1.0, 2.0, 3.0),
            angular_velocity_radps=(0.1, 0.2, 0.3),
        )
        self.assertEqual(imu.read_sample().angular_velocity_radps[2], 0.3)

    def test_lifecycle_and_unavailable_state(self) -> None:
        imu = MockIMU()
        with self.assertRaises(IMUReadError):
            imu.read_sample()

        imu.set_available(False)
        with self.assertRaises(IMUInitializationError):
            imu.initialize()

        imu.set_available(True)
        imu.initialize()
        imu.close()
        imu.close()
        with self.assertRaises(IMUReadError):
            imu.read_sample()


if __name__ == "__main__":
    unittest.main()
