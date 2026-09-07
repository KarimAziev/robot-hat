import math
import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.lsm6ds33 import LSM6DS33Config
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.imu.lsm6ds33 import LSM6DS33


def _little_endian(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestLSM6DS33(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sleep = Mock()
        self.imu = LSM6DS33(
            bus=cast(SMBusABC, self.bus),
            monotonic_ns=lambda: 123_456_789,
            sleep=self.sleep,
        )

    def initialize(self) -> None:
        self.bus.read_byte_data.return_value = 0x69
        self.imu.initialize()

    def test_initialize_validates_resets_and_configures_sensor(self) -> None:
        self.initialize()

        self.assertEqual(
            self.bus.read_byte_data.call_args_list,
            [call(0x6B, 0x0F), call(0x6B, 0x0F)],
        )
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [
                call(0x6B, 0x12, 0x01),
                call(0x6B, 0x12, 0x44),
                call(0x6B, 0x10, 0x40),
                call(0x6B, 0x11, 0x40),
            ],
        )
        self.sleep.assert_called_once_with(0.1)

        self.imu.initialize()
        self.sleep.assert_called_once_with(0.1)

    def test_initialize_rejects_wrong_identity_and_wraps_bus_errors(self) -> None:
        self.bus.read_byte_data.return_value = 0x00
        with self.assertRaisesRegex(IMUInitializationError, "WHO_AM_I mismatch"):
            self.imu.initialize()
        self.bus.write_byte_data.assert_not_called()

        self.bus.read_byte_data.side_effect = OSError("I2C unavailable")
        with self.assertRaisesRegex(IMUInitializationError, "failed to initialize"):
            self.imu.initialize()

    def test_reads_one_contiguous_native_little_endian_sample(self) -> None:
        self.initialize()
        self.bus.read_i2c_block_data.return_value = (
            _little_endian(1000)
            + _little_endian(-2000)
            + _little_endian(3000)
            + _little_endian(-4000)
            + _little_endian(5000)
            + _little_endian(-6000)
        )

        sample = self.imu.read_raw_sample()

        self.assertEqual(sample.gyroscope_counts, (1000, -2000, 3000))
        self.assertEqual(sample.accelerometer_counts, (-4000, 5000, -6000))
        self.assertEqual(sample.timestamp_monotonic_ns, 123_456_789)
        self.bus.read_i2c_block_data.assert_called_once_with(0x6B, 0x22, 12)

    def test_read_sample_converts_every_supported_special_range_to_si(self) -> None:
        self.imu = LSM6DS33(
            address=0x6A,
            bus=cast(SMBusABC, self.bus),
            config=LSM6DS33Config(
                accelerometer_range_g=16,
                gyroscope_range_dps=125,
                output_data_rate_hz=208,
            ),
            monotonic_ns=lambda: 42,
            sleep=self.sleep,
        )
        self.initialize()
        self.bus.read_i2c_block_data.return_value = (
            _little_endian(1000)
            + _little_endian(-1000)
            + _little_endian(0)
            + _little_endian(1000)
            + _little_endian(-1000)
            + _little_endian(0)
        )

        sample = self.imu.read_sample()

        self.assertAlmostEqual(sample.acceleration_mps2[0], 0.488 * 9.80665)
        self.assertAlmostEqual(sample.acceleration_mps2[1], -0.488 * 9.80665)
        self.assertAlmostEqual(sample.angular_velocity_radps[0], math.radians(4.375))
        self.assertAlmostEqual(sample.angular_velocity_radps[1], math.radians(-4.375))
        self.assertEqual(sample.timestamp_monotonic_ns, 42)

    def test_read_errors_lifecycle_and_ownership(self) -> None:
        with self.assertRaisesRegex(IMUReadError, "initialize"):
            self.imu.read_sample()

        self.initialize()
        self.bus.read_i2c_block_data.return_value = [0] * 11
        with self.assertRaisesRegex(IMUReadError, "11 of 12"):
            self.imu.read_sample()

        self.bus.read_i2c_block_data.side_effect = OSError("read failed")
        with self.assertRaisesRegex(IMUReadError, "failed to read"):
            self.imu.read_sample()

        self.imu.close()
        self.imu.close()
        self.bus.close.assert_not_called()
        with self.assertRaisesRegex(IMUReadError, "closed"):
            self.imu.read_sample()

        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned = LSM6DS33(bus=3, sleep=self.sleep)
        owned.close()
        owned.close()
        bus_class.assert_called_once_with(3)
        bus_class.return_value.close.assert_called_once_with()

    def test_rejects_an_address_not_supported_by_the_lsm6ds33(self) -> None:
        with self.assertRaisesRegex(ValueError, "0x6A or 0x6B"):
            LSM6DS33(address=0x36, bus=cast(SMBusABC, self.bus))


class TestLSM6DS33Config(unittest.TestCase):
    def test_encodes_ranges_rate_and_datasheet_sensitivities(self) -> None:
        config = LSM6DS33Config(
            accelerometer_range_g=8,
            gyroscope_range_dps=2000,
            output_data_rate_hz=1666,
        )

        self.assertEqual(config.accelerometer_control_register, 0x8C)
        self.assertEqual(config.gyroscope_control_register, 0x8C)
        self.assertAlmostEqual(config.accelerometer_mps2_per_lsb, 0.000244 * 9.80665)
        self.assertAlmostEqual(config.gyroscope_radps_per_lsb, math.radians(0.07))

    def test_encodes_non_linear_range_values(self) -> None:
        self.assertEqual(
            LSM6DS33Config(accelerometer_range_g=16).accelerometer_control_register,
            0x44,
        )
        self.assertEqual(
            LSM6DS33Config(gyroscope_range_dps=125).gyroscope_control_register,
            0x42,
        )


if __name__ == "__main__":
    unittest.main()
