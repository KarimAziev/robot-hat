import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.lis3mdl import LIS3MDLConfig
from robot_hat.exceptions import (
    MagnetometerInitializationError,
    MagnetometerReadError,
)
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.magnetometer.lis3mdl import LIS3MDL


def _little_endian(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestLIS3MDL(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sleep = Mock()
        self.bus.read_byte_data.return_value = 0x3D
        self.sensor = LIS3MDL(
            bus=cast(SMBusABC, self.bus),
            monotonic_ns=lambda: 321,
            sleep=self.sleep,
        )

    def test_initializes_with_pololu_reference_defaults(self) -> None:
        self.sensor.initialize()

        self.assertEqual(
            self.bus.read_byte_data.call_args_list,
            [call(0x1E, 0x0F), call(0x1E, 0x0F)],
        )
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [
                call(0x1E, 0x21, 0x04),
                call(0x1E, 0x20, 0x70),
                call(0x1E, 0x21, 0x00),
                call(0x1E, 0x22, 0x00),
                call(0x1E, 0x23, 0x0C),
                call(0x1E, 0x24, 0x40),
            ],
        )
        self.sleep.assert_called_once_with(0.01)

        self.sensor.initialize()
        self.sleep.assert_called_once_with(0.01)

    def test_reads_raw_counts_and_converts_to_teslas(self) -> None:
        self.sensor.initialize()
        self.bus.read_i2c_block_data.return_value = (
            _little_endian(6842) + _little_endian(-3421) + _little_endian(1711)
        )

        raw = self.sensor.read_raw_sample()
        sample = self.sensor.read_sample()

        self.assertEqual(raw.magnetic_field_counts, (6842, -3421, 1711))
        self.assertAlmostEqual(sample.magnetic_field_t[0], 1e-4)
        self.assertAlmostEqual(sample.magnetic_field_t[1], -0.5e-4)
        self.assertAlmostEqual(sample.magnetic_field_t[2], 1711e-4 / 6842)
        self.assertEqual(sample.timestamp_monotonic_ns, 321)
        self.bus.read_i2c_block_data.assert_called_with(0x1E, 0xA8, 6)

    def test_config_encodes_full_scale_rate_and_performance(self) -> None:
        config = LIS3MDLConfig(
            magnetic_field_range_gauss=16,
            output_data_rate_hz=80.0,
            performance_mode="high",
        )
        self.assertEqual(config.control_register_1, 0x5C)
        self.assertEqual(config.control_register_2, 0x60)
        self.assertEqual(config.control_register_4, 0x08)
        self.assertAlmostEqual(config.tesla_per_lsb, 1e-4 / 1711)

    def test_errors_lifecycle_and_ownership(self) -> None:
        with self.assertRaisesRegex(MagnetometerReadError, "initialize"):
            self.sensor.read_sample()

        self.bus.read_byte_data.return_value = 0
        with self.assertRaisesRegex(
            MagnetometerInitializationError, "WHO_AM_I mismatch"
        ):
            self.sensor.initialize()

        self.bus.read_byte_data.return_value = 0x3D
        self.sensor.initialize()
        self.bus.read_i2c_block_data.return_value = [0] * 5
        with self.assertRaisesRegex(MagnetometerReadError, "5 of 6"):
            self.sensor.read_sample()

        self.bus.read_i2c_block_data.side_effect = OSError("read failed")
        with self.assertRaisesRegex(MagnetometerReadError, "failed to read"):
            self.sensor.read_sample()

        self.sensor.close()
        self.sensor.close()
        self.bus.close.assert_not_called()
        with self.assertRaisesRegex(MagnetometerReadError, "closed"):
            self.sensor.read_sample()

        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned = LIS3MDL(bus=2)
        owned.close()
        owned.close()
        bus_class.assert_called_once_with(2)
        bus_class.return_value.close.assert_called_once_with()

    def test_rejects_an_address_not_supported_by_the_lis3mdl(self) -> None:
        with self.assertRaisesRegex(ValueError, "0x1C or 0x1E"):
            LIS3MDL(address=0x1D, bus=cast(SMBusABC, self.bus))


if __name__ == "__main__":
    unittest.main()
