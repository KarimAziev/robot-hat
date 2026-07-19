import unittest
from unittest.mock import patch

from robot_hat.data_types.uart import (
    UARTConfig,
    USBUARTDevice,
    USBUARTSelector,
)
from robot_hat.exceptions import UARTPortAmbiguousError, UARTPortNotFoundError
from robot_hat.mock.uart import MockUART
from robot_hat.uart.usb_uart import find_usb_uart_device


class TestUARTConfig(unittest.TestCase):
    def test_raspberry_pi_and_usb_paths_share_the_same_config(self) -> None:
        native = UARTConfig(port="/dev/serial0", baudrate=460800)
        usb = UARTConfig(port="/dev/ttyUSB0", baudrate=460800)

        self.assertEqual(native.baudrate, usb.baudrate)
        self.assertEqual(native.bytesize, 8)
        self.assertEqual(native.parity, "N")
        self.assertEqual(native.stopbits, 1)

    def test_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            UARTConfig(port="", baudrate=115200)
        with self.assertRaises(ValueError):
            UARTConfig(port="/dev/serial0", baudrate=0)
        with self.assertRaises(ValueError):
            UARTConfig(port="/dev/serial0", baudrate=115200, timeout=-1)


class TestMockUART(unittest.TestCase):
    def test_supports_partial_reads_and_queued_data(self) -> None:
        uart = MockUART(b"abc", max_read_size=1)
        uart.open()

        self.assertEqual(uart.read(3), b"a")
        uart.queue_read_data(b"de")
        self.assertEqual(uart.read(3), b"b")
        self.assertEqual(uart.write(b"command"), 7)
        self.assertEqual(uart.writes, [b"command"])


class TestUSBUARTDiscovery(unittest.TestCase):
    devices = [
        USBUARTDevice(
            port="/dev/ttyUSB0",
            description="CP2102 bridge",
            hardware_id="USB VID:PID=10C4:EA60",
            vendor_id=0x10C4,
            product_id=0xEA60,
            serial_number="LIDAR-A",
            manufacturer="Silicon Labs",
            product="CP2102 USB to UART Bridge",
        ),
        USBUARTDevice(
            port="/dev/ttyUSB1",
            description="CP2102 bridge",
            hardware_id="USB VID:PID=10C4:EA60",
            vendor_id=0x10C4,
            product_id=0xEA60,
            serial_number="LIDAR-B",
            manufacturer="Silicon Labs",
            product="CP2102 USB to UART Bridge",
        ),
    ]

    @patch("robot_hat.uart.usb_uart.list_usb_uart_devices", return_value=devices)
    def test_selects_by_usb_identity(self, _list_devices) -> None:
        device = find_usb_uart_device(
            USBUARTSelector(vendor_id=0x10C4, serial_number="LIDAR-B")
        )
        self.assertEqual(device.port, "/dev/ttyUSB1")

    @patch("robot_hat.uart.usb_uart.list_usb_uart_devices", return_value=devices)
    def test_rejects_ambiguous_selector(self, _list_devices) -> None:
        with self.assertRaises(UARTPortAmbiguousError):
            find_usb_uart_device(USBUARTSelector(product="cp2102"))

    @patch("robot_hat.uart.usb_uart.list_usb_uart_devices", return_value=devices)
    def test_rejects_missing_device(self, _list_devices) -> None:
        with self.assertRaises(UARTPortNotFoundError):
            find_usb_uart_device(USBUARTSelector(serial_number="missing"))


if __name__ == "__main__":
    unittest.main()
