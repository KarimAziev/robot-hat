import unittest

from robot_hat.drivers.angle.as5048a import AS5048ADiagnostics
from robot_hat.sensors.angular_position.as5048a_angular_position import (
    AS5048AAngularPosition,
)


class FakeAS5048A:
    def __init__(self) -> None:
        self.raw_angle = 4096
        self.closed = False

    def read_diagnostics(self) -> AS5048ADiagnostics:
        return AS5048ADiagnostics(True, False, False, False, 128, 0x180)

    def read_raw_angle(self) -> int:
        return self.raw_angle

    def read_angle_degrees(self) -> float:
        return self.raw_angle * 360.0 / 16_384

    def close(self) -> None:
        self.closed = True


class TestAS5048AAngularPosition(unittest.TestCase):
    def test_applies_software_zero_and_direction_without_owning_injected_sensor(
        self,
    ) -> None:
        sensor = FakeAS5048A()
        position = AS5048AAngularPosition(
            sensor=sensor,
            zero_offset_degrees=30,
            invert_direction=True,
            monotonic_ns=lambda: 123,
        )
        position.initialize()

        sample = position.read_angle()

        self.assertEqual(sample.angle_degrees, 300)
        self.assertEqual(sample.timestamp_monotonic_ns, 123)
        self.assertTrue(position.read_health().available)
        position.close()
        self.assertFalse(sensor.closed)


if __name__ == "__main__":
    unittest.main()
