"""Absolute angular-position sensor backed by the AS5048A."""

import math
import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.angular_position import (
    AngularPositionHealth,
    AngularPositionSample,
)
from robot_hat.drivers.angle.as5048a import (
    AS5048A,
    AS5048ADiagnostics,
    AS5048ASensor,
    DEFAULT_SPI_BUS,
    DEFAULT_SPI_DEVICE,
    DEFAULT_SPI_SPEED_HZ,
)
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.interfaces.angular_position_abc import AngularPositionABC
from robot_hat.interfaces.spi_abc import SPIABC


class AS5048AAngularPosition(AngularPositionABC):
    """AS5048A absolute position, optionally offset and direction-corrected."""

    def __init__(
        self,
        *,
        sensor: AS5048ASensor | None = None,
        spi: SPIABC | None = None,
        bus: int = DEFAULT_SPI_BUS,
        device: int = DEFAULT_SPI_DEVICE,
        max_speed_hz: int = DEFAULT_SPI_SPEED_HZ,
        zero_offset_degrees: float = 0.0,
        invert_direction: bool = False,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if sensor is not None and spi is not None:
            raise ValueError("sensor and spi cannot both be provided")
        if not math.isfinite(zero_offset_degrees):
            raise ValueError("zero_offset_degrees must be finite")
        self._sensor = (
            sensor
            if sensor is not None
            else AS5048A(
                spi=spi,
                bus=bus,
                device=device,
                max_speed_hz=max_speed_hz,
            )
        )
        self._owns_sensor = sensor is None
        self._zero_offset_degrees = float(zero_offset_degrees)
        self._invert_direction = invert_direction
        self._monotonic_ns = monotonic_ns
        self._lock = RLock()
        self._communication_errors = 0
        self._initialized = False
        self._closed = False

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("AS5048AAngularPosition is closed")
            self._initialized = False
            diagnostics = self._read_diagnostics()
            self._validate_magnet(diagnostics)
            self._read_raw_angle()
            self._initialized = True

    def read_angle(self) -> AngularPositionSample:
        with self._lock:
            self._require_initialized()
            diagnostics = self._read_diagnostics()
            self._validate_magnet(diagnostics)
            try:
                angle_degrees = self._sensor.read_angle_degrees()
            except Exception:
                self._communication_errors += 1
                raise
            angle_degrees = (angle_degrees - self._zero_offset_degrees) % 360.0
            if self._invert_direction:
                angle_degrees = (-angle_degrees) % 360.0
            return AngularPositionSample(
                angle_degrees=angle_degrees,
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def read_health(self) -> AngularPositionHealth:
        with self._lock:
            if self._closed:
                return self._health_without_diagnostics()
            try:
                diagnostics = self._sensor.read_diagnostics()
            except Exception:
                self._communication_errors += 1
                return self._health_without_diagnostics()
            return AngularPositionHealth(
                available=self._initialized and diagnostics.data_valid,
                magnet_detected=diagnostics.magnet_detected,
                magnet_too_weak=diagnostics.magnet_too_weak,
                magnet_too_strong=diagnostics.magnet_too_strong,
                communication_errors=self._communication_errors,
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            if self._owns_sensor:
                self._sensor.close()

    def __enter__(self) -> "AS5048AAngularPosition":
        self.initialize()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _read_diagnostics(self) -> AS5048ADiagnostics:
        try:
            return self._sensor.read_diagnostics()
        except Exception:
            self._communication_errors += 1
            raise

    def _read_raw_angle(self) -> int:
        try:
            return self._sensor.read_raw_angle()
        except Exception:
            self._communication_errors += 1
            raise

    def _require_initialized(self) -> None:
        if self._closed:
            raise RuntimeError("AS5048AAngularPosition is closed")
        if not self._initialized:
            raise EncoderNotInitializedError("call initialize() before sampling")

    @staticmethod
    def _validate_magnet(diagnostics: AS5048ADiagnostics) -> None:
        if not diagnostics.offset_compensation_finished:
            raise EncoderMagnetError("AS5048A offset compensation is not finished")
        if diagnostics.cordic_overflow:
            raise EncoderMagnetError("AS5048A CORDIC overflow makes angle invalid")
        if diagnostics.magnet_too_weak:
            raise EncoderMagnetError("AS5048A magnet field is too weak")
        if diagnostics.magnet_too_strong:
            raise EncoderMagnetError("AS5048A magnet field is too strong")

    def _health_without_diagnostics(self) -> AngularPositionHealth:
        return AngularPositionHealth(
            available=False,
            communication_errors=self._communication_errors,
        )


__all__ = ["AS5048AAngularPosition"]
