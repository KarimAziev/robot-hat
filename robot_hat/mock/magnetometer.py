"""Configurable hardware-free magnetometer."""

import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.magnetometer import MagneticFieldVector, MagnetometerSample
from robot_hat.exceptions import MagnetometerInitializationError, MagnetometerReadError
from robot_hat.interfaces.magnetometer_abc import MagnetometerABC


class MockMagnetometer(MagnetometerABC):
    def __init__(
        self,
        *,
        magnetic_field_t: MagneticFieldVector = (20e-6, 0.0, 45e-6),
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        MagnetometerSample(magnetic_field_t, 0)
        self._magnetic_field_t = magnetic_field_t
        self._monotonic_ns = monotonic_ns
        self._available = True
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise MagnetometerInitializationError("MockMagnetometer is closed")
            if not self._available:
                raise MagnetometerInitializationError("MockMagnetometer is unavailable")
            self._initialized = True

    def read_sample(self) -> MagnetometerSample:
        with self._lock:
            if self._closed:
                raise MagnetometerReadError("MockMagnetometer is closed")
            if not self._initialized:
                raise MagnetometerReadError("call initialize() before sampling")
            if not self._available:
                raise MagnetometerReadError("MockMagnetometer is unavailable")
            return MagnetometerSample(self._magnetic_field_t, self._monotonic_ns())

    def set_sample(self, magnetic_field_t: MagneticFieldVector) -> None:
        MagnetometerSample(magnetic_field_t, 0)
        with self._lock:
            self._magnetic_field_t = magnetic_field_t

    def set_available(self, available: bool) -> None:
        if not isinstance(available, bool):
            raise TypeError("available must be a bool")
        with self._lock:
            self._available = available

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False


__all__ = ["MockMagnetometer"]
