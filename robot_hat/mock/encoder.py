"""Configurable hardware-free encoder test double."""

import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.encoder import EncoderHealth, EncoderSample
from robot_hat.exceptions import EncoderNotInitializedError
from robot_hat.interfaces.encoder_abc import EncoderABC


class MockEncoder(EncoderABC):
    """Deterministic cumulative encoder with useful no-argument defaults."""

    def __init__(
        self,
        *,
        initial_ticks: int = 0,
        ticks_per_sample: int = 0,
        magnet_detected: bool | None = None,
        magnet_too_weak: bool | None = None,
        magnet_too_strong: bool | None = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._ticks = initial_ticks
        self._ticks_per_sample = ticks_per_sample
        self._magnet_detected = magnet_detected
        self._magnet_too_weak = magnet_too_weak
        self._magnet_too_strong = magnet_too_strong
        self._monotonic_ns = monotonic_ns
        self._communication_errors = 0
        self._invalid_transitions = 0
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("MockEncoder is closed")
            self._initialized = True

    def read_sample(self) -> EncoderSample:
        with self._lock:
            self._require_initialized()
            self._ticks += self._ticks_per_sample
            return EncoderSample(self._ticks, self._monotonic_ns())

    def reset(self, ticks: int = 0) -> None:
        with self._lock:
            self._require_initialized()
            self._ticks = ticks

    def read_health(self) -> EncoderHealth:
        with self._lock:
            return EncoderHealth(
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
                invalid_transitions=self._invalid_transitions,
            )

    def advance(self, ticks: int) -> None:
        """Move the counter explicitly without taking a sample."""
        with self._lock:
            self._ticks += ticks

    def set_error_counters(
        self, *, communication_errors: int, invalid_transitions: int
    ) -> None:
        """Configure diagnostics for estimator and failure-path tests."""
        if communication_errors < 0 or invalid_transitions < 0:
            raise ValueError("error counters must be non-negative")
        with self._lock:
            self._communication_errors = communication_errors
            self._invalid_transitions = invalid_transitions

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False

    def _require_initialized(self) -> None:
        if self._closed:
            raise RuntimeError("MockEncoder is closed")
        if not self._initialized:
            raise EncoderNotInitializedError("call initialize() before sampling")


__all__ = ["MockEncoder"]
