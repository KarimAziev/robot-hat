"""Configurable hardware-free angular-position test double."""

import math
import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.angular_position import (
    AngularPositionHealth,
    AngularPositionSample,
)
from robot_hat.exceptions import EncoderNotInitializedError
from robot_hat.interfaces.angular_position_abc import AngularPositionABC


class MockAngularPosition(AngularPositionABC):
    """Deterministic absolute-angle sensor with useful no-argument defaults."""

    def __init__(
        self,
        *,
        initial_angle_degrees: float = 0.0,
        degrees_per_sample: float = 0.0,
        magnet_detected: bool | None = None,
        magnet_too_weak: bool | None = None,
        magnet_too_strong: bool | None = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not math.isfinite(initial_angle_degrees):
            raise ValueError("initial_angle_degrees must be finite")
        if not math.isfinite(degrees_per_sample):
            raise ValueError("degrees_per_sample must be finite")
        self._angle_degrees = initial_angle_degrees % 360.0
        self._degrees_per_sample = degrees_per_sample
        self._magnet_detected = magnet_detected
        self._magnet_too_weak = magnet_too_weak
        self._magnet_too_strong = magnet_too_strong
        self._monotonic_ns = monotonic_ns
        self._communication_errors = 0
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("MockAngularPosition is closed")
            self._initialized = True

    def read_angle(self) -> AngularPositionSample:
        with self._lock:
            self._require_initialized()
            self._angle_degrees = (
                self._angle_degrees + self._degrees_per_sample
            ) % 360.0
            return AngularPositionSample(
                self._angle_degrees,
                self._monotonic_ns(),
            )

    def read_health(self) -> AngularPositionHealth:
        with self._lock:
            return AngularPositionHealth(
                available=(
                    self._initialized
                    and not self._closed
                    and self._magnet_detected is not False
                    and self._magnet_too_weak is not True
                    and self._magnet_too_strong is not True
                ),
                magnet_detected=self._magnet_detected,
                magnet_too_weak=self._magnet_too_weak,
                magnet_too_strong=self._magnet_too_strong,
                communication_errors=self._communication_errors,
            )

    def set_angle(self, angle_degrees: float) -> None:
        if not math.isfinite(angle_degrees):
            raise ValueError("angle_degrees must be finite")
        with self._lock:
            self._angle_degrees = angle_degrees % 360.0

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False

    def _require_initialized(self) -> None:
        if self._closed:
            raise RuntimeError("MockAngularPosition is closed")
        if not self._initialized:
            raise EncoderNotInitializedError("call initialize() before sampling")


__all__ = ["MockAngularPosition"]
