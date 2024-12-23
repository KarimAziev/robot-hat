import errno
import unittest
from typing import List, Optional
from unittest.mock import MagicMock, patch

from robot_hat.exceptions import ADCAddressNotFound
from robot_hat.i2c import I2C


class TestI2C(unittest.TestCase):

    @patch("robot_hat.i2c.SMBus")
    def test_initialize_successful(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus
        mock_bus.write_byte = MagicMock()

        with patch.object(I2C, "check_address", return_value=0x15):
            i2c: I2C = I2C(address=0x15)
            self.assertEqual(i2c.address, 0x15)

    @patch("robot_hat.i2c.SMBus")
    @patch("robot_hat.i2c.logger")
    def test_initialize_address_not_found(
        self, mock_logger: MagicMock, mock_smbus: MagicMock
    ) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(I2C, "check_address", return_value=None):
            with self.assertRaises(ADCAddressNotFound):
                I2C(address=0x99)

        mock_logger.error.assert_called_once_with("I2C address %s not found", 0x99)

    @patch("robot_hat.i2c.SMBus")
    def test_find_address_single_successful(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(I2C, "check_address", return_value=0x20):
            i2c: I2C = I2C(address=0x20)
            result: Optional[int] = i2c.find_address(0x20)
            self.assertEqual(result, 0x20)

    @patch("robot_hat.i2c.SMBus")
    def test_find_address_list(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(
            I2C, "check_address", side_effect=lambda x: x if x == 0x15 else None
        ):
            i2c: I2C = I2C(address=[0x10, 0x15, 0x20])
            self.assertEqual(i2c.address, 0x15)

    @patch("robot_hat.i2c.SMBus")
    def test_write_single_byte(self, mock_smbus: MagicMock) -> None:
        mock_smbus.return_value = MagicMock()
        i2c: I2C = I2C(address=0x15)

        with patch.object(i2c._smbus, "write_byte") as mock_write_byte:
            i2c.write(0xAB)
            mock_write_byte.assert_called_once_with(0x15, 0xAB)

    @patch("robot_hat.i2c.SMBus")
    def test_write_byte_data(self, mock_smbus: MagicMock) -> None:
        mock_smbus.return_value = MagicMock()
        i2c: I2C = I2C(address=0x15)

        with patch.object(i2c._smbus, "write_byte_data") as mock_write_byte_data:
            i2c.write([0x01, 0x02])
            mock_write_byte_data.assert_called_once_with(0x15, 0x01, 0x02)

    @patch("robot_hat.i2c.SMBus")
    def test_write_word_data(self, mock_smbus: MagicMock) -> None:
        mock_smbus.return_value = MagicMock()
        i2c: I2C = I2C(address=0x15)

        with patch.object(i2c._smbus, "write_word_data") as mock_write_word_data:
            i2c.write([0x01, 0xCD, 0xAB])
            mock_write_word_data.assert_called_once_with(0x15, 0x01, 0xABCD)

    @patch("robot_hat.i2c.SMBus")
    def test_write_block_data(self, mock_smbus: MagicMock) -> None:
        mock_smbus.return_value = MagicMock()
        i2c: I2C = I2C(address=0x15)

        with patch.object(i2c._smbus, "write_i2c_block_data") as mock_write_block:
            i2c.write([0x01, 0x20, 0x30, 0x40])
            mock_write_block.assert_called_once_with(0x15, 0x01, [0x20, 0x30, 0x40])

    @patch("robot_hat.i2c.SMBus")
    def test_read_byte(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_bus.read_byte.return_value = 0xAB
        mock_smbus.return_value = mock_bus

        i2c: I2C = I2C(address=0x15)
        result: List[int] = i2c.read(1)
        self.assertEqual(result, [0xAB])

    @patch("robot_hat.i2c.SMBus")
    def test_read_block_data(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_bus.read_i2c_block_data.return_value = [0x10, 0x20, 0x30]
        mock_smbus.return_value = mock_bus

        i2c: I2C = I2C(address=0x15)
        result: List[int] = i2c.mem_read(3, 0x01)
        self.assertEqual(result, [0x10, 0x20, 0x30])
        mock_bus.read_i2c_block_data.assert_called_once_with(0x15, 0x01, 3)

    @patch("robot_hat.i2c.SMBus")
    def test_scan_devices(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(
            mock_bus,
            "write_byte",
            side_effect=lambda addr, _: (
                None if addr in [0x10, 0x20] else OSError(errno.EREMOTEIO)
            ),
        ):
            i2c: I2C = I2C(address=0x10)
            devices: List[int] = i2c.scan()
            self.assertIn(0x10, devices)
            self.assertIn(0x20, devices)

    @patch("robot_hat.i2c.SMBus")
    def test_is_ready(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_bus.write_byte = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(I2C, "scan", return_value=[0x15]):
            i2c: I2C = I2C(address=0x15)
            self.assertTrue(i2c.is_ready())

    @patch("robot_hat.i2c.SMBus")
    def test_is_available(self, mock_smbus: MagicMock) -> None:
        mock_bus: MagicMock = MagicMock()
        mock_smbus.return_value = mock_bus

        with patch.object(I2C, "check_address", return_value=True):
            i2c: I2C = I2C(address=0x15)
            self.assertTrue(i2c.is_avaliable())


if __name__ == "__main__":
    unittest.main()
