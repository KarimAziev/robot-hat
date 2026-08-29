import unittest
from typing import Sequence
from unittest.mock import Mock, patch

from robot_hat.drivers.angle.as5048a import (
    AS5048A,
    AS5048AParityError,
    AS5048AProtocolError,
)
from robot_hat.interfaces.spi_abc import SPIABC
from robot_hat.mock.spi import MockAS5048ASPI
from robot_hat.spi.spidev_device import SpidevDevice


def response_frame(value: int, *, error: bool = False) -> list[int]:
    frame = value & 0x3FFF
    if error:
        frame |= 0x4000
    if frame.bit_count() % 2:
        frame |= 0x8000
    return [(frame >> 8) & 0xFF, frame & 0xFF]


class FakeSPI(SPIABC):
    def __init__(self, responses: list[list[int]]) -> None:
        self.responses = iter(responses)
        self.transfers: list[list[int]] = []
        self.closed = False

    def transfer(self, data: Sequence[int]) -> list[int]:
        self.transfers.append(list(data))
        return next(self.responses)

    def close(self) -> None:
        self.closed = True


class TestAS5048A(unittest.TestCase):
    def test_reads_pipelined_angle_with_even_command_parity(self) -> None:
        spi = FakeSPI([[0, 0], response_frame(0x1234), [0, 0], response_frame(0)])
        sensor = AS5048A(spi=spi)

        self.assertEqual(sensor.read_raw_angle(), 0x1234)
        self.assertAlmostEqual(sensor.read_angle_degrees(), 0.0)

        self.assertEqual(spi.transfers[:2], [[0xFF, 0xFF], [0x00, 0x00]])
        self.assertEqual(spi.transfers[2:], [[0xFF, 0xFF], [0x00, 0x00]])

    def test_decodes_magnetic_diagnostics_and_magnitude(self) -> None:
        raw = (1 << 8) | (1 << 10) | (1 << 11) | 37
        spi = FakeSPI(
            [
                [0, 0],
                response_frame(raw),
                [0, 0],
                response_frame(0x2345),
            ]
        )
        sensor = AS5048A(spi=spi)

        diagnostics = sensor.read_diagnostics()

        self.assertTrue(diagnostics.offset_compensation_finished)
        self.assertFalse(diagnostics.cordic_overflow)
        self.assertTrue(diagnostics.magnet_too_strong)
        self.assertTrue(diagnostics.magnet_too_weak)
        self.assertEqual(diagnostics.automatic_gain_control, 37)
        self.assertTrue(diagnostics.magnet_detected)
        self.assertFalse(diagnostics.data_valid)
        self.assertEqual(sensor.read_magnitude(), 0x2345)

    def test_rejects_bad_response_parity(self) -> None:
        spi = FakeSPI([[0, 0], [0x00, 0x01]])
        sensor = AS5048A(spi=spi)

        with self.assertRaises(AS5048AParityError):
            sensor.read_raw_angle()

    def test_clears_and_reports_sensor_protocol_error(self) -> None:
        spi = FakeSPI(
            [
                [0, 0],
                response_frame(0, error=True),
                [0, 0],
                response_frame(0b111),
            ]
        )
        sensor = AS5048A(spi=spi)

        with self.assertRaises(AS5048AProtocolError) as context:
            sensor.read_raw_angle()

        flags = context.exception.flags
        self.assertTrue(flags.framing_error)
        self.assertTrue(flags.invalid_command)
        self.assertTrue(flags.parity_error)
        self.assertEqual(spi.transfers[2:], [[0x40, 0x01], [0x00, 0x00]])

    def test_injected_spi_remains_open_and_owned_spi_closes_once(self) -> None:
        injected = FakeSPI([])
        sensor = AS5048A(spi=injected)
        sensor.close()
        sensor.close()
        self.assertFalse(injected.closed)
        with self.assertRaises(RuntimeError):
            sensor.read_raw_angle()

        with patch("robot_hat.spi.spidev_device.SpidevDevice") as device_class:
            owned = AS5048A(bus=1, device=2, max_speed_hz=2_000_000)
        owned.close()
        owned.close()
        device_class.assert_called_once_with(
            bus=1,
            device=2,
            mode=1,
            max_speed_hz=2_000_000,
            bits_per_word=8,
        )
        device_class.return_value.close.assert_called_once_with()

    def test_rejects_clock_above_datasheet_limit(self) -> None:
        with self.assertRaises(ValueError):
            AS5048A(spi=FakeSPI([]), max_speed_hz=10_000_001)

    def test_validates_linux_endpoint_even_with_an_injected_spi(self) -> None:
        with self.assertRaisesRegex(ValueError, "bus"):
            AS5048A(spi=FakeSPI([]), bus=-1)
        with self.assertRaisesRegex(ValueError, "device"):
            AS5048A(spi=FakeSPI([]), device=True)

    def test_automatic_mock_mode_avoids_spidev(self) -> None:
        with patch.dict("os.environ", {"ROBOT_HAT_MOCK_SPI": "1"}):
            sensor = AS5048A()

        self.assertEqual(sensor.read_raw_angle(), 0)
        self.assertTrue(sensor.read_diagnostics().data_valid)
        self.assertTrue(sensor.owns_spi)
        self.assertIsInstance(sensor.spi, MockAS5048ASPI)
        mock_spi = sensor.spi
        assert isinstance(mock_spi, MockAS5048ASPI)
        sensor.close()
        self.assertTrue(mock_spi.closed)


class TestSpidevDevice(unittest.TestCase):
    def test_configures_mode_one_endpoint_and_validates_transfers(self) -> None:
        handle = Mock()
        handle.xfer2.return_value = [0x12, 0x34]
        module = Mock()
        module.SpiDev.return_value = handle

        with patch("robot_hat.spi.spidev_device.import_module", return_value=module):
            device = SpidevDevice(
                bus=0,
                device=1,
                mode=1,
                max_speed_hz=1_000_000,
            )

        self.assertEqual(device.transfer([0xAA, 0x55]), [0x12, 0x34])
        handle.open.assert_called_once_with(0, 1)
        self.assertEqual(handle.mode, 1)
        self.assertEqual(handle.max_speed_hz, 1_000_000)
        self.assertEqual(handle.bits_per_word, 8)
        with self.assertRaises(ValueError):
            device.transfer([256])
        device.close()
        device.close()
        handle.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
