import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.lps25h import LPS25HConfig
from robot_hat.exceptions import (
    EnvironmentalSensorInitializationError,
    EnvironmentalSensorReadError,
)
from robot_hat.interfaces.smbus_abc import SMBusABC
from robot_hat.sensors.environmental.lps25h import LPS25H


def _little_endian_i16(value: int) -> List[int]:
    unsigned = value & 0xFFFF
    return [unsigned & 0xFF, unsigned >> 8]


class TestLPS25H(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.sleep = Mock()
        self.bus.read_byte_data.return_value = 0xBD
        self.sensor = LPS25H(
            bus=cast(SMBusABC, self.bus),
            monotonic_ns=lambda: 987,
            sleep=self.sleep,
        )

    def test_initializes_lps25h_or_lps25hb_and_converts_sample(self) -> None:
        self.sensor.initialize()
        pressure_counts = round(1013.25 * 4096)
        pressure = [
            pressure_counts & 0xFF,
            pressure_counts >> 8 & 0xFF,
            pressure_counts >> 16 & 0xFF,
        ]
        self.bus.read_i2c_block_data.return_value = pressure + _little_endian_i16(-8400)

        sample = self.sensor.read_sample()

        self.assertAlmostEqual(sample.pressure_pa or 0.0, 101_325.0)
        self.assertAlmostEqual(sample.temperature_c or 0.0, 25.0)
        self.assertIsNone(sample.relative_humidity_percent)
        self.assertEqual(sample.timestamp_monotonic_ns, 987)
        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [
                call(0x5C, 0x21, 0x04),
                call(0x5C, 0x10, 0x05),
                call(0x5C, 0x20, 0x94),
            ],
        )
        self.sleep.assert_called_once_with(0.01)
        self.bus.read_i2c_block_data.assert_called_once_with(0x5C, 0xA8, 5)

    def test_errors_lifecycle_and_ownership(self) -> None:
        with self.assertRaisesRegex(EnvironmentalSensorReadError, "initialize"):
            self.sensor.read_sample()
        self.bus.read_byte_data.return_value = 0
        with self.assertRaisesRegex(
            EnvironmentalSensorInitializationError, "WHO_AM_I mismatch"
        ):
            self.sensor.initialize()
        self.bus.read_byte_data.return_value = 0xBD
        self.sensor.initialize()
        self.bus.read_i2c_block_data.return_value = [0] * 4
        with self.assertRaisesRegex(EnvironmentalSensorReadError, "4 of 5"):
            self.sensor.read_sample()
        self.sensor.close()
        self.bus.close.assert_not_called()

        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned = LPS25H(bus=2)
        owned.close()
        bus_class.return_value.close.assert_called_once_with()

    def test_accepts_both_addresses_and_encodes_output_rates(self) -> None:
        alternate = LPS25H(address=0x5D, bus=cast(SMBusABC, self.bus))
        self.assertEqual(alternate.address, 0x5D)
        self.assertEqual(LPS25HConfig(output_data_rate_hz=25.0).control_register, 0xC4)
        with self.assertRaisesRegex(ValueError, "0x5C or 0x5D"):
            LPS25H(address=0x5F, bus=cast(SMBusABC, self.bus))


if __name__ == "__main__":
    unittest.main()
