import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.lsm9ds1_magnetometer import (
    LSM9DS1MagnetometerConfig,
)
from robot_hat.exceptions import (
    MagnetometerInitializationError,
    MagnetometerReadError,
)
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.magnetometer.lsm9ds1 import LSM9DS1Magnetometer


def _little_endian(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestLSM9DS1Magnetometer(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sleep = Mock()
        self.bus.read_byte_data.return_value = 0x3D
        self.sensor = LSM9DS1Magnetometer(
            bus=cast(SMBusABC, self.bus),
            monotonic_ns=lambda: 321,
            sleep=self.sleep,
        )

    def test_initializes_and_converts_native_axes_to_teslas(self) -> None:
        self.sensor.initialize()
        self.bus.read_i2c_block_data.return_value = (
            _little_endian(1000) + _little_endian(-2000) + _little_endian(3000)
        )

        raw = self.sensor.read_raw_sample()
        sample = self.sensor.read_sample()

        self.assertEqual(raw.magnetic_field_counts, (1000, -2000, 3000))
        self.assertAlmostEqual(sample.magnetic_field_t[0], 14e-6)
        self.assertAlmostEqual(sample.magnetic_field_t[1], -28e-6)
        self.assertAlmostEqual(sample.magnetic_field_t[2], 42e-6)
        self.assertEqual(sample.timestamp_monotonic_ns, 321)
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [
                call(0x1C, 0x21, 0x04),
                call(0x1C, 0x20, 0xF4),
                call(0x1C, 0x21, 0x00),
                call(0x1C, 0x22, 0x00),
                call(0x1C, 0x23, 0x0C),
                call(0x1C, 0x24, 0x40),
            ],
        )
        self.bus.read_i2c_block_data.assert_called_with(0x1C, 0xA8, 6)

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
        self.sensor.close()
        self.bus.close.assert_not_called()

        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned = LSM9DS1Magnetometer(bus=2)
        owned.close()
        bus_class.return_value.close.assert_called_once_with()

    def test_config_encodes_full_scale_rate_and_performance(self) -> None:
        config = LSM9DS1MagnetometerConfig(
            magnetic_field_range_gauss=16,
            output_data_rate_hz=80.0,
            performance_mode="high",
        )
        self.assertEqual(config.control_register_1, 0xDC)
        self.assertEqual(config.control_register_2, 0x60)
        self.assertEqual(config.control_register_4, 0x08)
        self.assertAlmostEqual(config.tesla_per_lsb, 0.58e-7)


if __name__ == "__main__":
    unittest.main()
