"""Cumulative encoder backed by the AS5600L absolute angle sensor."""

import logging
import math
import time
from threading import RLock
from typing import Callable, Final

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.encoder import EncoderHealth, EncoderSample
from robot_hat.drivers.angle.as5600l import (
    AS5600L,
    AS5600LStatus,
    DEFAULT_ADDRESS,
    FULL_SCALE_COUNTS,
)
from robot_hat.exceptions import EncoderMagnetError, EncoderNotInitializedError
from robot_hat.interfaces.encoder_abc import EncoderABC


_log = logging.getLogger(__name__)
DEFAULT_MAX_SAMPLE_GAP_NS: Final = 100_000_000
DEFAULT_MAX_ABS_SPEED_RPS: Final = 5.0
_HALF_SCALE: Final = FULL_SCALE_COUNTS // 2


class AS5600LEncoder(EncoderABC):
    """Thread-safe signed cumulative encoder with 4096 ticks per revolution.

    Safe single-turn unwrapping requires less than half a revolution between
    samples. ``max_abs_speed_rps`` derives that physical interval, while
    ``max_sample_gap_ns`` may impose a stricter scheduling limit. Reaching either
    limit re-baselines without inventing motion and increments diagnostics.
    """

    def __init__(
        self,
        *,
        bus: BusType = 1,
        address: int = DEFAULT_ADDRESS,
        invert_direction: bool = False,
        max_sample_gap_ns: int | None = DEFAULT_MAX_SAMPLE_GAP_NS,
        max_abs_speed_rps: float | None = DEFAULT_MAX_ABS_SPEED_RPS,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if max_sample_gap_ns is not None:
            if isinstance(max_sample_gap_ns, bool) or not isinstance(
                max_sample_gap_ns, int
            ):
                raise TypeError("max_sample_gap_ns must be an integer or None")
            if max_sample_gap_ns <= 0:
                raise ValueError("max_sample_gap_ns must be positive or None")
        if max_abs_speed_rps is not None:
            if isinstance(max_abs_speed_rps, bool) or not isinstance(
                max_abs_speed_rps, (int, float)
            ):
                raise TypeError("max_abs_speed_rps must be a number or None")
            if not math.isfinite(max_abs_speed_rps) or max_abs_speed_rps <= 0:
                raise ValueError("max_abs_speed_rps must be finite and positive")
        self._sensor = AS5600L(bus=bus, address=address)
        self._invert_direction = invert_direction
        self._max_sample_gap_ns = max_sample_gap_ns
        self._max_abs_speed_rps = (
            float(max_abs_speed_rps) if max_abs_speed_rps is not None else None
        )
        self._maximum_unambiguous_gap_ns = (
            int(0.5 / self._max_abs_speed_rps * 1_000_000_000)
            if self._max_abs_speed_rps is not None
            else None
        )
        self._monotonic_ns = monotonic_ns
        self._lock = RLock()
        self._ticks = 0
        self._last_raw_angle: int | None = None
        self._last_sample_ns: int | None = None
        self._communication_errors = 0
        self._invalid_transitions = 0
        self._initialized = False
        self._closed = False

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("AS5600LEncoder is closed")
            self._initialized = False
            self._last_raw_angle = None
            self._last_sample_ns = None
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                raise
            self._validate_magnet(status)
            try:
                raw_angle = self._sensor.read_raw_angle()
            except Exception:
                self._communication_errors += 1
                raise
            self._last_raw_angle = raw_angle
            self._last_sample_ns = self._monotonic_ns()
            self._initialized = True

    def read_sample(self) -> EncoderSample:
        with self._lock:
            self._require_initialized()
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                raise
            try:
                self._validate_magnet(status)
            except EncoderMagnetError:
                self._invalid_transitions += 1
                self._last_raw_angle = None
                self._last_sample_ns = None
                raise
            try:
                raw_angle = self._sensor.read_raw_angle()
            except Exception:
                self._communication_errors += 1
                raise
            timestamp_ns = self._monotonic_ns()
            last_raw_angle = self._last_raw_angle
            last_sample_ns = self._last_sample_ns
            if last_raw_angle is None or last_sample_ns is None:
                self._last_raw_angle = raw_angle
                self._last_sample_ns = timestamp_ns
                return EncoderSample(
                    ticks=self._ticks,
                    timestamp_monotonic_ns=timestamp_ns,
                )

            gap_ns = timestamp_ns - last_sample_ns
            if gap_ns < 0:
                self._invalid_transitions += 1
                _log.warning("AS5600L monotonic clock moved backwards")
            elif self._gap_is_ambiguous(gap_ns):
                self._invalid_transitions += 1
                _log.warning(
                    "AS5600L sample gap %d ns reached an unwrap safety limit; "
                    "re-baselining",
                    gap_ns,
                )
            else:
                delta = raw_angle - last_raw_angle
                if delta == _HALF_SCALE or delta == -_HALF_SCALE:
                    self._invalid_transitions += 1
                    _log.warning("AS5600L transition of half a turn is ambiguous")
                else:
                    if delta > _HALF_SCALE:
                        delta -= FULL_SCALE_COUNTS
                    elif delta < -_HALF_SCALE:
                        delta += FULL_SCALE_COUNTS
                    if self._invert_direction:
                        delta = -delta
                    self._ticks += delta

            self._last_raw_angle = raw_angle
            self._last_sample_ns = timestamp_ns
            return EncoderSample(
                ticks=self._ticks,
                timestamp_monotonic_ns=timestamp_ns,
            )

    def reset(self, ticks: int = 0) -> None:
        if isinstance(ticks, bool) or not isinstance(ticks, int):
            raise TypeError("ticks must be an integer")
        with self._lock:
            self._require_initialized()
            self._ticks = ticks

    def read_health(self) -> EncoderHealth:
        with self._lock:
            if self._closed:
                return self._health_without_status()
            try:
                status = self._sensor.read_status()
            except Exception:
                self._communication_errors += 1
                return self._health_without_status()
            return EncoderHealth(
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
                invalid_transitions=self._invalid_transitions,
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            self._sensor.close()

    def __enter__(self) -> "AS5600LEncoder":
        self.initialize()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_initialized(self) -> None:
        if self._closed:
            raise RuntimeError("AS5600LEncoder is closed")
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

    def _health_without_status(self) -> EncoderHealth:
        return EncoderHealth(
            available=False,
            communication_errors=self._communication_errors,
            invalid_transitions=self._invalid_transitions,
        )

    def _gap_is_ambiguous(self, gap_ns: int) -> bool:
        limits = (
            limit
            for limit in (
                self._max_sample_gap_ns,
                self._maximum_unambiguous_gap_ns,
            )
            if limit is not None
        )
        return any(gap_ns >= limit for limit in limits)


__all__ = [
    "AS5600LEncoder",
    "DEFAULT_MAX_ABS_SPEED_RPS",
    "DEFAULT_MAX_SAMPLE_GAP_NS",
]
