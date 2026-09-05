import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.hts221 import HTS221Config
from robot_hat.exceptions import (
    EnvironmentalSensorInitializationError,
    EnvironmentalSensorReadError,
)
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.environmental.hts221 import HTS221


def _little_endian(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestHTS221(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sensor = HTS221(bus=cast(SMBusABC, self.bus), monotonic_ns=lambda: 123_456)
        calibration_bytes = {
            0x30: 40,  # 20 %RH
            0x31: 160,  # 80 %RH
            0x32: 0,  # 0 C * 8
            0x33: 64,  # low byte of 40 C * 8
            0x35: 0x04,  # high bits of 40 C * 8
        }
        self.bus.read_byte_data.side_effect = lambda _address, register: (
            0xBC if register == 0x0F else calibration_bytes[register]
        )
        calibration_words = {
            0xB6: _little_endian(0),
            0xBA: _little_endian(1000),
            0xBC: _little_endian(0),
            0xBE: _little_endian(1000),
        }
        self.bus.read_i2c_block_data.side_effect = lambda _address, register, _length: (
            calibration_words[register]
        )

    def test_initializes_and_applies_factory_calibration(self) -> None:
        self.sensor.initialize()
        self.bus.read_i2c_block_data.side_effect = None
        self.bus.read_i2c_block_data.return_value = _little_endian(
            500
        ) + _little_endian(500)

        sample = self.sensor.read_sample()

        self.assertAlmostEqual(sample.relative_humidity_percent or 0.0, 50.0)
        self.assertAlmostEqual(sample.temperature_c or 0.0, 20.0)
        self.assertIsNone(sample.pressure_pa)
        self.assertEqual(sample.timestamp_monotonic_ns, 123_456)
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [call(0x5F, 0x10, 0x1B), call(0x5F, 0x20, 0x85)],
        )
        self.bus.read_i2c_block_data.assert_called_with(0x5F, 0xA8, 4)

    def test_rejects_identity_and_degenerate_calibration(self) -> None:
        self.bus.read_byte_data.side_effect = None
        self.bus.read_byte_data.return_value = 0
        with self.assertRaisesRegex(
            EnvironmentalSensorInitializationError, "WHO_AM_I mismatch"
        ):
            self.sensor.initialize()

        self.setUp()
        self.bus.read_i2c_block_data.side_effect = None
        self.bus.read_i2c_block_data.return_value = _little_endian(0)
        with self.assertRaisesRegex(
            EnvironmentalSensorInitializationError, "coincident ADC points"
        ):
            self.sensor.initialize()

    def test_lifecycle_malformed_read_and_ownership(self) -> None:
        with self.assertRaisesRegex(EnvironmentalSensorReadError, "initialize"):
            self.sensor.read_sample()
        self.sensor.initialize()
        self.bus.read_i2c_block_data.side_effect = None
        self.bus.read_i2c_block_data.return_value = [0, 1]
        with self.assertRaisesRegex(EnvironmentalSensorReadError, "2 of 4"):
            self.sensor.read_sample()
        self.sensor.close()
        self.bus.close.assert_not_called()

        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned = HTS221(bus=2)
        owned.close()
        bus_class.return_value.close.assert_called_once_with()

    def test_config_encodes_rate_and_averaging(self) -> None:
        config = HTS221Config(
            output_data_rate_hz=12.5,
            humidity_average_samples=512,
            temperature_average_samples=256,
        )
        self.assertEqual(config.control_register, 0x87)
        self.assertEqual(config.averaging_register, 0x3F)


if __name__ == "__main__":
    unittest.main()
