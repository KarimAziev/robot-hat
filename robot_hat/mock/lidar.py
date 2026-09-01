"""Configurable hardware-free planar LiDAR."""

import math
import time
from threading import Event, RLock
from typing import Callable, Iterator

from robot_hat.data_types.lidar import (
    LidarDeviceInfo,
    LidarHealth,
    LidarHealthStatus,
    LidarMeasurement,
)
from robot_hat.exceptions import LidarConnectionError, LidarStateError
from robot_hat.interfaces.lidar_2d_abc import Lidar2DABC


class MockLidar2D(Lidar2DABC):
    """Repeat a uniform 360-degree scan using the real LiDAR contract.

    ``scan_frequency_hz=None`` produces scans without waiting and is convenient
    for unit tests. A positive frequency uses an interruptible wait between
    revolutions so application shutdown does not have to wait for a sleep.
    """

    def __init__(
        self,
        *,
        points_per_scan: int = 36,
        distance_m: float = 2.0,
        quality: int = 100,
        scan_frequency_hz: float | None = 10.0,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if isinstance(points_per_scan, bool) or not isinstance(points_per_scan, int):
            raise TypeError("points_per_scan must be an integer")
        if points_per_scan < 2:
            raise ValueError("points_per_scan must be at least two")
        self._validate_distance(distance_m)
        self._validate_quality(quality)
        if scan_frequency_hz is not None:
            if (
                isinstance(scan_frequency_hz, bool)
                or not isinstance(scan_frequency_hz, (int, float))
                or not math.isfinite(scan_frequency_hz)
                or scan_frequency_hz <= 0
            ):
                raise ValueError("scan_frequency_hz must be finite and positive")
        self._points_per_scan = points_per_scan
        self._distance_m = float(distance_m)
        self._quality = quality
        self._scan_period_s = (
            1.0 / float(scan_frequency_hz) if scan_frequency_hz is not None else None
        )
        self._monotonic = monotonic
        self._health = LidarHealth(LidarHealthStatus.OK)
        self._connected = False
        self._scanning = False
        self._stop_event = Event()
        self._lock = RLock()

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._connected

    @property
    def is_scanning(self) -> bool:
        with self._lock:
            return self._scanning

    def connect(self) -> None:
        with self._lock:
            self._connected = True

    def disconnect(self) -> None:
        self.stop_scan()
        with self._lock:
            self._connected = False

    def get_device_info(self) -> LidarDeviceInfo:
        self._require_connected()
        return LidarDeviceInfo(
            manufacturer="robot-hat",
            model="MockLidar2D",
            serial_number="MOCK-0001",
            firmware_version="1.0",
            hardware_version="virtual",
        )

    def get_health(self) -> LidarHealth:
        self._require_connected()
        with self._lock:
            return self._health

    def set_health(
        self,
        status: LidarHealthStatus,
        *,
        error_code: int | None = None,
    ) -> None:
        """Replace the health returned to application startup checks."""

        with self._lock:
            self._health = LidarHealth(status=status, error_code=error_code)

    def reset(self) -> None:
        self._require_connected()
        self.stop_scan()

    def start_scan(self) -> None:
        self._require_connected()
        with self._lock:
            if self._scanning:
                return
            self._stop_event.clear()
            self._scanning = True

    def stop_scan(self) -> None:
        with self._lock:
            self._scanning = False
            self._stop_event.set()

    def iter_measurements(self) -> Iterator[LidarMeasurement]:
        if not self.is_scanning:
            raise LidarStateError("call start_scan() before iterating measurements")
        while self.is_scanning:
            with self._lock:
                distance_m = self._distance_m
                quality = self._quality
            started_at = self._monotonic()
            for index in range(self._points_per_scan):
                if not self.is_scanning:
                    return
                yield LidarMeasurement(
                    angle_deg=index * 360.0 / self._points_per_scan,
                    distance_m=distance_m,
                    quality=quality,
                    start_of_scan=index == 0,
                    timestamp=started_at,
                )
            if self._scan_period_s is not None:
                self._stop_event.wait(self._scan_period_s)

    def set_uniform_scan(
        self, *, distance_m: float, quality: int | None = None
    ) -> None:
        """Change the range returned for every angle on future revolutions."""

        self._validate_distance(distance_m)
        if quality is not None:
            self._validate_quality(quality)
        with self._lock:
            self._distance_m = float(distance_m)
            if quality is not None:
                self._quality = quality

    def _require_connected(self) -> None:
        if not self.is_connected:
            raise LidarConnectionError("MockLidar2D is not connected")

    @staticmethod
    def _validate_distance(distance_m: float) -> None:
        if (
            isinstance(distance_m, bool)
            or not isinstance(distance_m, (int, float))
            or not math.isfinite(distance_m)
            or distance_m < 0
        ):
            raise ValueError("distance_m must be finite and non-negative")

    @staticmethod
    def _validate_quality(quality: int) -> None:
        if (
            isinstance(quality, bool)
            or not isinstance(quality, int)
            or not 0 <= quality <= 255
        ):
            raise ValueError("quality must be an integer in [0, 255]")


__all__ = ["MockLidar2D"]
