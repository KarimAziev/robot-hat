import unittest

from robot_hat.data_types.config.lidar import RPLidarC1Config
from robot_hat.data_types.lidar import LidarHealthStatus
from robot_hat.exceptions import (
    LidarConnectionError,
    LidarProtocolError,
    LidarStateError,
    LidarTimeoutError,
)
from robot_hat.mock.uart import MockUART
from robot_hat.sensors.lidar.rplidar_c1 import RPLidarC1


def descriptor(payload_size: int, send_mode: int, data_type: int) -> bytes:
    size_and_mode = payload_size | (send_mode << 30)
    return b"\xa5\x5a" + size_and_mode.to_bytes(4, "little") + bytes((data_type,))


def measurement(
    angle_deg: float,
    distance_m: float,
    quality: int = 15,
    *,
    start: bool = False,
) -> bytes:
    sync_bits = 0x01 if start else 0x02
    sync_quality = (quality << 2) | sync_bits
    angle_and_check = (round(angle_deg * 64.0) << 1) | 0x01
    distance_q2_mm = round(distance_m * 4000.0)
    return (
        bytes((sync_quality,))
        + angle_and_check.to_bytes(2, "little")
        + distance_q2_mm.to_bytes(2, "little")
    )


class TestRPLidarC1Config(unittest.TestCase):
    def test_c1_defaults_match_reference_driver(self) -> None:
        config = RPLidarC1Config()
        self.assertEqual(config.port, "/dev/ttyUSB0")
        self.assertEqual(config.baudrate, 460800)
        self.assertEqual(config.uart_config.bytesize, 8)
        self.assertEqual(config.uart_config.parity, "N")


class TestRPLidarC1(unittest.TestCase):
    def setUp(self) -> None:
        self.config = RPLidarC1Config(reset_wait_s=0, stop_wait_s=0)
        self.uart = MockUART(max_read_size=2, config=self.config.uart_config)
        self.lidar = RPLidarC1(self.config, uart=self.uart)

    def test_operations_require_connection(self) -> None:
        with self.assertRaises(LidarConnectionError):
            self.lidar.get_health()
        with self.assertRaises(LidarConnectionError):
            self.lidar.start_scan()

    def test_reads_device_info_across_partial_uart_reads(self) -> None:
        serial_number = bytes(range(16))
        payload = bytes((0x41,)) + (0x011D).to_bytes(2, "little") + bytes((6,))
        self.uart.queue_read_data(
            b"noise" + descriptor(20, 0, 0x04) + payload + serial_number
        )
        self.lidar.connect()

        info = self.lidar.get_device_info()

        self.assertEqual(info.manufacturer, "Slamtec")
        self.assertEqual(info.model, "C1M1")
        self.assertEqual(info.firmware_version, "1.29")
        self.assertEqual(info.hardware_version, "6")
        self.assertEqual(info.serial_number, serial_number.hex().upper())
        self.assertEqual(self.uart.writes, [b"\xa5\x50"])

    def test_reads_warning_health_and_error_code(self) -> None:
        self.uart.queue_read_data(descriptor(3, 0, 0x06) + bytes((1, 0x34, 0x12)))
        self.lidar.connect()

        health = self.lidar.get_health()

        self.assertEqual(health.status, LidarHealthStatus.WARNING)
        self.assertTrue(health.is_usable)
        self.assertEqual(health.error_code, 0x1234)

    def test_rejects_an_unexpected_descriptor(self) -> None:
        self.uart.queue_read_data(descriptor(4, 0, 0x06))
        self.lidar.connect()

        with self.assertRaisesRegex(LidarProtocolError, "Expected 3 response bytes"):
            self.lidar.get_health()

    def test_times_out_on_short_response(self) -> None:
        self.uart.queue_read_data(b"\xa5")
        self.lidar.connect()

        with self.assertRaises(LidarTimeoutError):
            self.lidar.get_health()

    def test_decodes_standard_measurements_and_resynchronizes(self) -> None:
        scan_header = descriptor(5, 1, 0x81)
        self.uart.queue_read_data(
            scan_header
            + b"\x00"
            + measurement(90.0, 2.5, quality=23, start=True)
            + measurement(180.0, 1.25, quality=7)
        )
        self.lidar.connect()
        self.lidar.start_scan()

        iterator = self.lidar.iter_measurements()
        first = next(iterator)
        second = next(iterator)

        self.assertTrue(first.start_of_scan)
        self.assertAlmostEqual(first.angle_deg, 270.0)
        self.assertAlmostEqual(first.distance_m, 2.5)
        self.assertEqual(first.quality, 23)
        self.assertAlmostEqual(first.x_m, 0.0, places=7)
        self.assertAlmostEqual(first.y_m, -2.5)
        self.assertFalse(second.start_of_scan)
        self.assertAlmostEqual(second.angle_deg, 180.0)
        self.assertEqual(self.uart.writes[0], b"\xa5\x20")

    def test_groups_only_complete_revolutions_for_slam(self) -> None:
        self.uart.queue_read_data(
            descriptor(5, 1, 0x81)
            + measurement(300.0, 1.0)
            + measurement(0.0, 1.1, start=True)
            + measurement(90.0, 1.2)
            + measurement(180.0, 1.3)
            + measurement(0.0, 1.4, start=True)
        )
        self.lidar.connect()
        self.lidar.start_scan()

        scan = next(self.lidar.iter_scans(min_measurements=3, max_scans=1))

        self.assertEqual(len(scan.measurements), 3)
        self.assertEqual(
            [point.angle_deg for point in scan.measurements],
            [0.0, 270.0, 180.0],
        )
        self.assertGreaterEqual(scan.duration_s, 0.0)

    def test_query_is_rejected_during_scan(self) -> None:
        self.uart.queue_read_data(descriptor(5, 1, 0x81))
        self.lidar.connect()
        self.lidar.start_scan()

        with self.assertRaises(LidarStateError):
            self.lidar.get_device_info()

    def test_failed_scan_start_sends_stop_and_restores_idle_state(self) -> None:
        self.uart.queue_read_data(descriptor(4, 1, 0x81))
        self.lidar.connect()

        with self.assertRaisesRegex(LidarProtocolError, "Expected 5-byte"):
            self.lidar.start_scan()

        self.assertFalse(self.lidar.is_scanning)
        self.assertEqual(self.uart.writes, [b"\xa5\x20", b"\xa5\x25"])

    def test_stop_reset_and_injected_uart_ownership(self) -> None:
        self.uart.queue_read_data(descriptor(5, 1, 0x81))
        self.lidar.connect()
        self.lidar.start_scan()
        self.lidar.stop_scan()
        self.lidar.reset()
        self.lidar.disconnect()

        self.assertEqual(
            self.uart.writes,
            [b"\xa5\x20", b"\xa5\x25", b"\xa5\x40"],
        )
        self.assertTrue(self.uart.is_open)


if __name__ == "__main__":
    unittest.main()
