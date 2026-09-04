import math
import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.lsm9ds1 import LSM9DS1Config
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.imu.lsm9ds1 import LSM9DS1


def _little_endian(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestLSM9DS1(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sleep = Mock()
        self.imu = LSM9DS1(
            bus=cast(SMBusABC, self.bus),
            monotonic_ns=lambda: 123_456_789,
            sleep=self.sleep,
        )

    def initialize(self) -> None:
        self.bus.read_byte_data.return_value = 0x68
        self.imu.initialize()

    def test_initialize_validates_resets_and_configures_sensor(self) -> None:
        self.initialize()

        self.assertEqual(
            self.bus.read_byte_data.call_args_list,
            [call(0x6A, 0x0F), call(0x6A, 0x0F)],
        )
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [
                call(0x6A, 0x22, 0x01),
                call(0x6A, 0x22, 0x44),
                call(0x6A, 0x10, 0x60),
                call(0x6A, 0x12, 0x00),
                call(0x6A, 0x1E, 0x38),
                call(0x6A, 0x1F, 0x38),
                call(0x6A, 0x20, 0x60),
                call(0x6A, 0x21, 0x00),
            ],
        )
        self.sleep.assert_called_once_with(0.1)

        self.imu.initialize()
        self.sleep.assert_called_once_with(0.1)

    def test_initialize_rejects_wrong_identity_without_writing(self) -> None:
        self.bus.read_byte_data.return_value = 0x00

        with self.assertRaisesRegex(IMUInitializationError, "WHO_AM_I mismatch"):
            self.imu.initialize()

        self.bus.write_byte_data.assert_not_called()

    def test_initialize_wraps_bus_errors(self) -> None:
        self.bus.read_byte_data.side_effect = OSError("I2C unavailable")

        with self.assertRaisesRegex(IMUInitializationError, "failed to initialize"):
            self.imu.initialize()

    def test_read_raw_sample_decodes_native_little_endian_axes(self) -> None:
        self.initialize()
        self.bus.read_i2c_block_data.side_effect = [
            _little_endian(1000) + _little_endian(-2000) + _little_endian(3000),
            _little_endian(-4000) + _little_endian(5000) + _little_endian(-6000),
        ]

        sample = self.imu.read_raw_sample()

        self.assertEqual(sample.gyroscope_counts, (1000, -2000, 3000))
        self.assertEqual(sample.accelerometer_counts, (-4000, 5000, -6000))
        self.assertEqual(sample.timestamp_monotonic_ns, 123_456_789)
        self.assertEqual(
            self.bus.read_i2c_block_data.call_args_list,
            [call(0x6A, 0x18, 6), call(0x6A, 0x28, 6)],
        )

    def test_read_sample_converts_configured_ranges_to_si_units(self) -> None:
        self.imu = LSM9DS1(
            bus=cast(SMBusABC, self.bus),
            config=LSM9DS1Config(
                accelerometer_range_g=4,
                gyroscope_range_dps=500,
                output_data_rate_hz=238,
            ),
            monotonic_ns=lambda: 42,
            sleep=self.sleep,
        )
        self.initialize()
        self.bus.read_i2c_block_data.side_effect = [
            _little_endian(1000) + _little_endian(-1000) + _little_endian(0),
            _little_endian(1000) + _little_endian(-1000) + _little_endian(0),
        ]

        sample = self.imu.read_sample()

        self.assertAlmostEqual(sample.acceleration_mps2[0], 0.122 * 9.80665)
        self.assertAlmostEqual(sample.acceleration_mps2[1], -0.122 * 9.80665)
        self.assertAlmostEqual(sample.angular_velocity_radps[0], math.radians(17.5))
        self.assertAlmostEqual(sample.angular_velocity_radps[1], math.radians(-17.5))
        self.assertEqual(sample.timestamp_monotonic_ns, 42)

    def test_read_requires_initialization_and_rejects_short_blocks(self) -> None:
        with self.assertRaisesRegex(IMUReadError, "initialize"):
            self.imu.read_sample()

        self.initialize()
        self.bus.read_i2c_block_data.return_value = [0] * 5
        with self.assertRaisesRegex(IMUReadError, "5 of 6"):
            self.imu.read_sample()

    def test_close_does_not_close_injected_bus(self) -> None:
        self.initialize()
        self.imu.close()
        self.imu.close()

        self.bus.close.assert_not_called()
        with self.assertRaisesRegex(IMUReadError, "closed"):
            self.imu.read_sample()

    def test_closes_bus_created_from_numeric_bus_id(self) -> None:
        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned_imu = LSM9DS1(bus=3, sleep=self.sleep)

        owned_imu.close()
        owned_imu.close()

        bus_class.assert_called_once_with(3)
        bus_class.return_value.close.assert_called_once_with()

    def test_rejects_an_address_not_supported_by_the_lsm9ds1(self) -> None:
        with self.assertRaisesRegex(ValueError, "0x6A or 0x6B"):
            LSM9DS1(address=0x36, bus=cast(SMBusABC, self.bus))


class TestLSM9DS1Config(unittest.TestCase):
    def test_encodes_ranges_rate_and_datasheet_sensitivities(self) -> None:
        config = LSM9DS1Config(
            accelerometer_range_g=16,
            gyroscope_range_dps=2000,
            output_data_rate_hz=238,
        )

        self.assertEqual(config.accelerometer_control_register, 0x88)
        self.assertEqual(config.gyroscope_control_register, 0x98)
        self.assertAlmostEqual(config.accelerometer_mps2_per_lsb, 0.000732 * 9.80665)
        self.assertAlmostEqual(config.gyroscope_radps_per_lsb, math.radians(0.07))


if __name__ == "__main__":
    unittest.main()
