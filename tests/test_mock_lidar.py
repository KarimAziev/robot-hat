import unittest

from robot_hat import LidarHealthStatus, MockLidar2D
from robot_hat.exceptions import LidarConnectionError, LidarStateError


class TestMockLidar2D(unittest.TestCase):
    def test_repeats_complete_scans_without_hardware(self) -> None:
        clock = iter(float(value) for value in range(10)).__next__
        lidar = MockLidar2D(
            points_per_scan=4,
            distance_m=3.0,
            scan_frequency_hz=None,
            monotonic=clock,
        )
        lidar.connect()
        self.assertEqual(lidar.get_device_info().model, "MockLidar2D")
        self.assertTrue(lidar.get_health().is_usable)
        lidar.start_scan()

        scans = list(lidar.iter_scans(min_measurements=4, max_scans=2))

        self.assertEqual(len(scans), 2)
        self.assertEqual(
            [point.angle_deg for point in scans[0].measurements],
            [0.0, 90.0, 180.0, 270.0],
        )
        self.assertTrue(all(point.distance_m == 3.0 for point in scans[0].measurements))

    def test_updates_scan_health_and_lifecycle(self) -> None:
        lidar = MockLidar2D(points_per_scan=2, scan_frequency_hz=None)
        with self.assertRaises(LidarConnectionError):
            lidar.get_health()
        with self.assertRaises(LidarStateError):
            next(lidar.iter_measurements())

        lidar.connect()
        lidar.set_health(LidarHealthStatus.WARNING, error_code=7)
        self.assertEqual(lidar.get_health().error_code, 7)
        lidar.set_uniform_scan(distance_m=0.5, quality=42)
        lidar.start_scan()
        measurement = next(lidar.iter_measurements())
        self.assertEqual(measurement.distance_m, 0.5)
        self.assertEqual(measurement.quality, 42)

        lidar.disconnect()
        lidar.disconnect()
        self.assertFalse(lidar.is_connected)
        self.assertFalse(lidar.is_scanning)


if __name__ == "__main__":
    unittest.main()
