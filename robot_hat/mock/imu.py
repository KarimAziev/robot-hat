"""Configurable hardware-free six-axis IMU."""

import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.imu import IMUSample, Vector3
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.interfaces.imu_abc import IMUABC


class MockIMU(IMUABC):
    """Deterministic IMU with stationary, level no-argument defaults."""

    def __init__(
        self,
        *,
        acceleration_mps2: Vector3 = (0.0, 0.0, 9.80665),
        angular_velocity_radps: Vector3 = (0.0, 0.0, 0.0),
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._validate_sample(acceleration_mps2, angular_velocity_radps)
        self._acceleration_mps2 = acceleration_mps2
        self._angular_velocity_radps = angular_velocity_radps
        self._monotonic_ns = monotonic_ns
        self._available = True
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise IMUInitializationError("MockIMU is closed")
            if not self._available:
                raise IMUInitializationError("MockIMU is unavailable")
            self._initialized = True

    def read_sample(self) -> IMUSample:
        with self._lock:
            if self._closed:
                raise IMUReadError("MockIMU is closed")
            if not self._initialized:
                raise IMUReadError("call initialize() before sampling")
            if not self._available:
                raise IMUReadError("MockIMU is unavailable")
            return IMUSample(
                acceleration_mps2=self._acceleration_mps2,
                angular_velocity_radps=self._angular_velocity_radps,
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def set_sample(
        self,
        *,
        acceleration_mps2: Vector3,
        angular_velocity_radps: Vector3,
    ) -> None:
        """Replace the values returned by subsequent samples."""

        self._validate_sample(acceleration_mps2, angular_velocity_radps)
        with self._lock:
            self._acceleration_mps2 = acceleration_mps2
            self._angular_velocity_radps = angular_velocity_radps

    def set_available(self, available: bool) -> None:
        """Enable or disable reads for failure-path testing."""

        if not isinstance(available, bool):
            raise TypeError("available must be a bool")
        with self._lock:
            self._available = available

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False

    @staticmethod
    def _validate_sample(
        acceleration_mps2: Vector3,
        angular_velocity_radps: Vector3,
    ) -> None:
        IMUSample(
            acceleration_mps2=acceleration_mps2,
            angular_velocity_radps=angular_velocity_radps,
            timestamp_monotonic_ns=0,
        )


__all__ = ["MockIMU"]
