import unittest
from unittest.mock import patch

from robot_hat.drivers.angle.as5600l import AS5600LStatus
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.mock.angular_position import MockAngularPosition
from robot_hat.sensors.angular_position.as5600l_angular_position import (
    AS5600LAngularPosition,
)


class FakeAS5600L:
    def __init__(self, *, angle_degrees: float, status: AS5600LStatus) -> None:
        self.angle_degrees = angle_degrees
        self.status = status
        self.closed = False

    def read_status(self) -> AS5600LStatus:
        return self.status

    def read_raw_angle(self) -> int:
        return 0

    def read_angle_degrees(self) -> float:
        return self.angle_degrees

    def close(self) -> None:
        self.closed = True


class TestAS5600LAngularPosition(unittest.TestCase):
    def test_reads_timestamped_offset_and_inverted_absolute_angle(self) -> None:
        sensor = FakeAS5600L(
            angle_degrees=30.0,
            status=AS5600LStatus(True, False, False, 0x20),
        )
        with patch(
            "robot_hat.sensors.angular_position.as5600l_angular_position.AS5600L",
            return_value=sensor,
        ):
            angular = AS5600LAngularPosition(
                zero_offset_degrees=10.0,
                invert_direction=True,
                monotonic_ns=lambda: 123,
            )
        with self.assertRaises(EncoderNotInitializedError):
            angular.read_angle()

        angular.initialize()
        sample = angular.read_angle()

        self.assertEqual(sample.angle_degrees, 340.0)
        self.assertEqual(sample.timestamp_monotonic_ns, 123)
        self.assertTrue(angular.read_health().available)
        angular.close()
        self.assertTrue(sensor.closed)

    def test_rejects_bad_magnet_without_counting_communication_error(self) -> None:
        sensor = FakeAS5600L(
            angle_degrees=0.0,
            status=AS5600LStatus(False, False, False, 0),
        )
        with patch(
            "robot_hat.sensors.angular_position.as5600l_angular_position.AS5600L",
            return_value=sensor,
        ):
            angular = AS5600LAngularPosition()

        with self.assertRaises(EncoderMagnetError):
            angular.initialize()
        self.assertEqual(angular.read_health().communication_errors, 0)


class TestMockAngularPosition(unittest.TestCase):
    def test_configurable_mock_works_without_hardware(self) -> None:
        angular = MockAngularPosition(
            initial_angle_degrees=350.0,
            degrees_per_sample=15.0,
            monotonic_ns=lambda: 42,
        )
        angular.initialize()

        sample = angular.read_angle()

        self.assertEqual(sample.angle_degrees, 5.0)
        self.assertEqual(sample.timestamp_monotonic_ns, 42)
        self.assertTrue(angular.read_health().available)


if __name__ == "__main__":
    unittest.main()
