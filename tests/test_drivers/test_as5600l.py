import unittest
from typing import Dict, List, cast
from unittest.mock import Mock, call, patch

from robot_hat.drivers.angle.as5600l import (
    AS5600L,
    AS5600LAddressProgrammer,
    AS5600LFastFilterThreshold,
    AS5600LSlowFilter,
)
from robot_hat.interfaces.smbus_abc import SMBusABC


class TestAS5600L(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock(spec=SMBusABC)
        self.driver = AS5600L(bus=cast(SMBusABC, self.bus), address=0x40)

    def test_reads_big_endian_angle_status_magnitude_and_gain(self) -> None:
        self.bus.read_i2c_block_data.side_effect = [
            [0x0A, 0xBC],
            [0x0A, 0xBC],
            [0x01, 0x23],
        ]
        self.bus.read_byte_data.side_effect = [0x38, 77]

        self.assertEqual(self.driver.read_raw_angle(), 0xABC)
        self.assertAlmostEqual(self.driver.read_angle_degrees(), 0xABC * 360.0 / 4096)
        status = self.driver.read_status()
        self.assertTrue(status.magnet_detected)
        self.assertTrue(status.magnet_too_weak)
        self.assertTrue(status.magnet_too_strong)
        self.assertEqual(self.driver.read_magnitude(), 0x123)
        self.assertEqual(self.driver.read_gain(), 77)

    def test_configure_filter_preserves_unrelated_configuration_bits(self) -> None:
        self.bus.read_i2c_block_data.return_value = [0x21, 0xA5]

        self.driver.configure_filter(
            slow_filter=AS5600LSlowFilter.X4,
            fast_filter_threshold=AS5600LFastFilterThreshold.LSB_18,
        )

        self.bus.write_i2c_block_data.assert_called_once_with(0x40, 0x07, [0x32, 0xA5])

    def test_temporary_address_is_encoded_and_applied_without_burn(self) -> None:
        self.driver.set_temporary_address(0x42)

        self.assertEqual(
            self.bus.write_byte_data.call_args_list,
            [call(0x40, 0x20, 0x84), call(0x40, 0x21, 0x84)],
        )
        self.assertEqual(self.driver.address, 0x42)
        self.assertNotIn(
            call(0x40, 0xFF, 0x40), self.bus.write_byte_data.call_args_list
        )

    def test_rejects_reserved_addresses_and_does_not_close_injected_bus(self) -> None:
        with self.assertRaises(ValueError):
            AS5600L(bus=cast(SMBusABC, self.bus), address=0x07)
        with self.assertRaises(ValueError):
            self.driver.set_temporary_address(0x78)

        self.driver.close()
        self.driver.close()

        self.bus.close.assert_not_called()
        with self.assertRaises(RuntimeError):
            self.driver.read_raw_angle()

    def test_rejects_malformed_register_read(self) -> None:
        self.bus.read_i2c_block_data.return_value = [0x12]

        with self.assertRaises(OSError):
            self.driver.read_raw_angle()

    def test_closes_bus_created_from_numeric_bus_id(self) -> None:
        with patch("robot_hat.i2c.i2c_bus.I2CBus") as bus_class:
            owned_driver = AS5600L(bus=3)

        owned_driver.close()
        owned_driver.close()

        bus_class.assert_called_once_with(3)
        bus_class.return_value.close.assert_called_once_with()


class TestAS5600LAddressProgrammer(unittest.TestCase):
    def setUp(self) -> None:
        self.registers: Dict[int, List[int]] = {
            0x05: [0x00, 0x00],
            0x07: [0x01, 0x23],
        }
        self.byte_registers: Dict[int, int] = {0x0B: 0x20, 0x20: 0x80}
        self.bus = Mock(spec=SMBusABC)
        self.bus.read_i2c_block_data.side_effect = self._read_block
        self.bus.read_byte_data.side_effect = self._read_byte
        self.bus.write_byte_data.side_effect = self._write_byte
        self.programmer = AS5600LAddressProgrammer(
            bus=cast(SMBusABC, self.bus),
            sleep=lambda _seconds: None,
        )

    def _read_block(self, _address: int, register: int, length: int) -> List[int]:
        return self.registers[register][:length]

    def _read_byte(self, _address: int, register: int) -> int:
        return self.byte_registers[register]

    def _write_byte(self, _address: int, register: int, value: int) -> None:
        if register == 0x20:
            self.byte_registers[register] = value

    def test_requires_exact_address_specific_confirmation(self) -> None:
        with self.assertRaises(ValueError):
            self.programmer.program_address(0x42, confirmation="yes")

        self.bus.write_byte_data.assert_not_called()

    def test_burns_and_verifies_readback_only_through_programmer(self) -> None:
        phrase = self.programmer.confirmation_phrase(0x42)

        result = self.programmer.program_address(0x42, confirmation=phrase)

        self.assertEqual(result.old_address, 0x40)
        self.assertEqual(result.new_address, 0x42)
        self.assertEqual(result.configuration, 0x123)
        self.assertTrue(result.otp_readback_verified)
        self.assertTrue(result.power_cycle_verification_required)
        burn_values = [
            one_call.args[2]
            for one_call in self.bus.write_byte_data.call_args_list
            if one_call.args[1] == 0xFF
        ]
        self.assertEqual(burn_values, [0x40, 0x01, 0x11, 0x10])


if __name__ == "__main__":
    unittest.main()
