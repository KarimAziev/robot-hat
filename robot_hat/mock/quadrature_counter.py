"""Deterministic hardware-free quadrature counter backend."""

import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.quadrature import QuadratureCounterSnapshot
from robot_hat.exceptions import (
    EncoderBackendError,
    EncoderClosedError,
    EncoderNotInitializedError,
)
from robot_hat.interfaces.quadrature_counter_backend_abc import (
    QuadratureCounterBackendABC,
)


class MockQuadratureCounterBackend(QuadratureCounterBackendABC):
    """Controllable atomic counter with useful zero-argument defaults.

    The mock has no background worker. Tests explicitly advance or set its
    count, inject invalid-transition diagnostics, and configure read failures.
    """

    def __init__(
        self,
        *,
        initial_count: int = 0,
        invalid_transitions: int = 0,
        available: bool = True,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._validate_count(initial_count)
        self._validate_diagnostic_count(invalid_transitions)
        self._count = initial_count
        self._invalid_transitions = invalid_transitions
        self._available = available
        self._monotonic_ns = monotonic_ns
        self._read_error: Exception | None = None
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    @property
    def initialized(self) -> bool:
        with self._lock:
            return self._initialized

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise EncoderClosedError("MockQuadratureCounterBackend is closed")
            self._initialized = True

    def read_snapshot(self) -> QuadratureCounterSnapshot:
        with self._lock:
            self._require_initialized()
            if self._read_error is not None:
                raise self._read_error
            if not self._available:
                raise EncoderBackendError("mock quadrature counter is unavailable")
            return QuadratureCounterSnapshot(
                count=self._count,
                timestamp_monotonic_ns=self._monotonic_ns(),
                invalid_transitions=self._invalid_transitions,
            )

    def reset(self, count: int = 0) -> None:
        self._validate_count(count)
        with self._lock:
            self._require_initialized()
            self._count = count

    def advance(self, counts: int) -> None:
        """Add positive or negative decoded counts atomically."""

        self._validate_count(counts)
        with self._lock:
            self._require_initialized()
            self._count += counts

    def set_count(self, count: int) -> None:
        """Set the absolute decoded count atomically."""

        self.reset(count)

    def inject_invalid_transitions(self, count: int = 1) -> None:
        """Add a non-negative number of invalid-transition diagnostics."""

        self._validate_diagnostic_count(count)
        with self._lock:
            self._require_initialized()
            self._invalid_transitions += count

    def set_available(self, available: bool) -> None:
        """Control whether snapshot reads report the backend as available."""

        if not isinstance(available, bool):
            raise TypeError("available must be a bool")
        with self._lock:
            self._available = available

    def set_read_error(self, error: Exception | None) -> None:
        """Raise ``error`` from reads until it is cleared with ``None``."""

        if error is not None and not isinstance(error, Exception):
            raise TypeError("error must be an Exception or None")
        with self._lock:
            self._read_error = error

    def close(self) -> None:
        with self._lock:
            self._closed = True
            self._initialized = False

    def _require_initialized(self) -> None:
        if self._closed:
            raise EncoderClosedError("MockQuadratureCounterBackend is closed")
        if not self._initialized:
            raise EncoderNotInitializedError(
                "call initialize() before reading the quadrature counter"
            )

    @staticmethod
    def _validate_count(count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer")

    @staticmethod
    def _validate_diagnostic_count(count: int) -> None:
        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("diagnostic count must be an integer")
        if count < 0:
            raise ValueError("diagnostic count must be non-negative")


__all__ = ["MockQuadratureCounterBackend"]
