"""EncoderABC adapter for a vendor-neutral quadrature counter backend."""

from threading import RLock

from robot_hat.data_types.encoder import EncoderHealth, EncoderSample
from robot_hat.exceptions import (
    EncoderBackendError,
    EncoderClosedError,
    EncoderNotInitializedError,
)
from robot_hat.interfaces.encoder_abc import EncoderABC
from robot_hat.interfaces.quadrature_counter_backend_abc import (
    QuadratureCounterBackendABC,
)


class QuadratureEncoder(EncoderABC):
    """Expose one atomic quadrature counter as a signed cumulative encoder.

    Direction inversion is applied only in this adapter so every backend can
    retain its natural electrical direction. By default the encoder owns the
    injected backend and closes it. Pass ``owns_backend=False`` for an explicitly
    shared backend; closing the encoder then leaves that backend open.
    """

    def __init__(
        self,
        *,
        backend: QuadratureCounterBackendABC,
        invert_direction: bool = False,
        owns_backend: bool = True,
    ) -> None:
        if not isinstance(backend, QuadratureCounterBackendABC):
            raise TypeError("backend must implement QuadratureCounterBackendABC")
        if not isinstance(invert_direction, bool):
            raise TypeError("invert_direction must be a bool")
        if not isinstance(owns_backend, bool):
            raise TypeError("owns_backend must be a bool")
        self._backend = backend
        self._invert_direction = invert_direction
        self._owns_backend = owns_backend
        self._communication_errors = 0
        self._last_invalid_transitions = 0
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise EncoderClosedError("QuadratureEncoder is closed")
            try:
                self._backend.initialize()
            except Exception as error:
                self._initialized = False
                self._communication_errors += 1
                raise EncoderBackendError(
                    "quadrature counter initialization failed"
                ) from error
            self._initialized = True

    def read_sample(self) -> EncoderSample:
        with self._lock:
            self._require_initialized()
            try:
                snapshot = self._backend.read_snapshot()
            except Exception as error:
                self._communication_errors += 1
                raise EncoderBackendError(
                    "quadrature counter snapshot failed"
                ) from error
            self._last_invalid_transitions = snapshot.invalid_transitions
            ticks = -snapshot.count if self._invert_direction else snapshot.count
            return EncoderSample(
                ticks=ticks,
                timestamp_monotonic_ns=snapshot.timestamp_monotonic_ns,
            )

    def read_health(self) -> EncoderHealth:
        with self._lock:
            if self._closed or not self._initialized:
                return self._health(available=False)
            try:
                snapshot = self._backend.read_snapshot()
            except Exception:
                self._communication_errors += 1
                return self._health(available=False)
            self._last_invalid_transitions = snapshot.invalid_transitions
            return self._health(available=True)

    def reset(self, ticks: int = 0) -> None:
        if isinstance(ticks, bool) or not isinstance(ticks, int):
            raise TypeError("ticks must be an integer")
        with self._lock:
            self._require_initialized()
            backend_count = -ticks if self._invert_direction else ticks
            try:
                self._backend.reset(backend_count)
            except Exception as error:
                self._communication_errors += 1
                raise EncoderBackendError("quadrature counter reset failed") from error

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            if not self._owns_backend:
                return
            try:
                self._backend.close()
            except Exception as error:
                self._communication_errors += 1
                raise EncoderBackendError("quadrature counter close failed") from error

    def __enter__(self) -> "QuadratureEncoder":
        self.initialize()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _require_initialized(self) -> None:
        if self._closed:
            raise EncoderClosedError("QuadratureEncoder is closed")
        if not self._initialized:
            raise EncoderNotInitializedError("call initialize() before sampling")

    def _health(self, *, available: bool) -> EncoderHealth:
        return EncoderHealth(
            available=available,
            communication_errors=self._communication_errors,
            invalid_transitions=self._last_invalid_transitions,
        )


__all__ = ["QuadratureEncoder"]
