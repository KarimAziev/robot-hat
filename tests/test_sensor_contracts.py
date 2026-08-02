import math
import unittest

from robot_hat.data_types.encoder import EncoderSample
from robot_hat.data_types.config.sh3001 import SH3001Config
from robot_hat.data_types.imu import IMUSample


class TestIMUSample(unittest.TestCase):
    def test_accepts_finite_si_vectors(self) -> None:
        sample = IMUSample(
            acceleration_mps2=(0.0, 0.0, 9.80665),
            angular_velocity_radps=(0.0, 0.0, 0.1),
            timestamp_monotonic_ns=42,
        )

        self.assertEqual(sample.timestamp_monotonic_ns, 42)

    def test_rejects_non_finite_axes_and_negative_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            IMUSample((math.nan, 0.0, 0.0), (0.0, 0.0, 0.0), 1)
        with self.assertRaises(ValueError):
            IMUSample((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), -1)


class TestEncoderSample(unittest.TestCase):
    def test_allows_signed_cumulative_ticks(self) -> None:
        sample = EncoderSample(ticks=-123, timestamp_monotonic_ns=42)

        self.assertEqual(sample.ticks, -123)

    def test_rejects_negative_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            EncoderSample(ticks=0, timestamp_monotonic_ns=-1)


class TestSH3001Config(unittest.TestCase):
    def test_exposes_matching_registers_and_sensitivities(self) -> None:
        config = SH3001Config(
            accelerometer_range_g=8,
            gyroscope_range_dps=500,
        )

        self.assertEqual(config.accelerometer_range_register, 0x03)
        self.assertEqual(config.accelerometer_lsb_per_g, 4096.0)
        self.assertEqual(config.gyroscope_range_register, 0x04)
        self.assertEqual(config.gyroscope_lsb_per_dps, 65.5)


if __name__ == "__main__":
    unittest.main()
