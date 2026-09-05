"""Configurable hardware-free environmental sensor."""

import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.environment import EnvironmentalSample
from robot_hat.exceptions import (
    EnvironmentalSensorInitializationError,
    EnvironmentalSensorReadError,
)
from robot_hat.interfaces.environmental_sensor_abc import EnvironmentalSensorABC


class MockEnvironmentalSensor(EnvironmentalSensorABC):
    def __init__(
        self,
        *,
        temperature_c: float | None = 21.0,
        relative_humidity_percent: float | None = 45.0,
        pressure_pa: float | None = 101_325.0,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._monotonic_ns = monotonic_ns
        self._values = (temperature_c, relative_humidity_percent, pressure_pa)
        self._validate_values()
        self._available = True
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise EnvironmentalSensorInitializationError(
                    "MockEnvironmentalSensor is closed"
                )
            if not self._available:
                raise EnvironmentalSensorInitializationError(
                    "MockEnvironmentalSensor is unavailable"
                )
            self._initialized = True

    def read_sample(self) -> EnvironmentalSample:
        with self._lock:
            if self._closed:
                raise EnvironmentalSensorReadError("MockEnvironmentalSensor is closed")
            if not self._initialized:
                raise EnvironmentalSensorReadError("call initialize() before sampling")
            if not self._available:
                raise EnvironmentalSensorReadError(
                    "MockEnvironmentalSensor is unavailable"
                )
            return EnvironmentalSample(
                temperature_c=self._values[0],
                relative_humidity_percent=self._values[1],
                pressure_pa=self._values[2],
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def set_sample(
        self,
        *,
        temperature_c: float | None,
        relative_humidity_percent: float | None,
        pressure_pa: float | None,
    ) -> None:
        EnvironmentalSample(
            temperature_c=temperature_c,
            relative_humidity_percent=relative_humidity_percent,
            pressure_pa=pressure_pa,
            timestamp_monotonic_ns=0,
        )
        with self._lock:
            self._values = (temperature_c, relative_humidity_percent, pressure_pa)

    def set_available(self, available: bool) -> None:
        if not isinstance(available, bool):
            raise TypeError("available must be a bool")
        with self._lock:
            self._available = available

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False

    def _validate_values(self) -> None:
        EnvironmentalSample(
            temperature_c=self._values[0],
            relative_humidity_percent=self._values[1],
            pressure_pa=self._values[2],
            timestamp_monotonic_ns=0,
        )


__all__ = ["MockEnvironmentalSensor"]
