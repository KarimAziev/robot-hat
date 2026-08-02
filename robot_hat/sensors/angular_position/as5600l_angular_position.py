"""Absolute angular-position sensor backed by the AS5600L."""

import math
import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.angular_position import (
    AngularPositionHealth,
    AngularPositionSample,
)
from robot_hat.data_types.bus import BusType
from robot_hat.drivers.angle.as5600l import AS5600L, DEFAULT_ADDRESS, AS5600LStatus
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.interfaces.angular_position_abc import AngularPositionABC


class AS5600LAngularPosition(AngularPositionABC):
    """AS5600L absolute position, optionally offset and direction-corrected."""

    def __init__(
        self,
        *,
        bus: BusType = 1,
        address: int = DEFAULT_ADDRESS,
        zero_offset_degrees: float = 0.0,
        invert_direction: bool = False,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not math.isfinite(zero_offset_degrees):
            raise ValueError("zero_offset_degrees must be finite")
        self._sensor = AS5600L(bus=bus, address=address)
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
                raise RuntimeError("AS5600LAngularPosition is closed")
            self._initialized = False
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                raise
            self._validate_magnet(status)
            try:
                self._sensor.read_raw_angle()
            except Exception:
                self._communication_errors += 1
                raise
            self._initialized = True

    def read_angle(self) -> AngularPositionSample:
        with self._lock:
            self._require_initialized()
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                raise
            self._validate_magnet(status)
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
                return AngularPositionHealth(
                    available=False,
                    communication_errors=self._communication_errors,
                )
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                return AngularPositionHealth(
                    available=False,
                    communication_errors=self._communication_errors,
                )
            return AngularPositionHealth(
                available=(
                    self._initialized
                    and status.magnet_detected
                    and not status.magnet_too_weak
                    and not status.magnet_too_strong
                ),
                magnet_detected=status.magnet_detected,
                magnet_too_weak=status.magnet_too_weak,
                magnet_too_strong=status.magnet_too_strong,
                communication_errors=self._communication_errors,
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            self._sensor.close()

    def __enter__(self) -> "AS5600LAngularPosition":
        self.initialize()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_initialized(self) -> None:
        if self._closed:
            raise RuntimeError("AS5600LAngularPosition is closed")
        if not self._initialized:
            raise EncoderNotInitializedError("call initialize() before sampling")

    @staticmethod
    def _validate_magnet(status: AS5600LStatus) -> None:
        if not status.magnet_detected:
            raise EncoderMagnetError("AS5600L magnet was not detected")
        if status.magnet_too_weak:
            raise EncoderMagnetError("AS5600L magnet field is too weak")
        if status.magnet_too_strong:
            raise EncoderMagnetError("AS5600L magnet field is too strong")


__all__ = ["AS5600LAngularPosition"]
