"""Reference GPIO A/B edge-capture backend for incremental encoders."""

import logging
import time
from threading import RLock
from typing import Callable

from robot_hat.data_types.quadrature import (
    QuadratureCounterSnapshot,
    QuadratureDecodeMode,
)
from robot_hat.exceptions import (
    EncoderBackendError,
    EncoderClosedError,
    EncoderNotInitializedError,
)
from robot_hat.interfaces.digital_edge_input_abc import DigitalEdgeInputABC
from robot_hat.interfaces.quadrature_counter_backend_abc import (
    QuadratureCounterBackendABC,
)
from robot_hat.sensors.encoder.quadrature_decoder import QuadratureDecoder


_log = logging.getLogger(__name__)


class GPIOQuadratureCounterBackend(QuadratureCounterBackendABC):
    """Decode two raw GPIO edge inputs into an atomic cumulative count.

    This is a reference and low-rate backend. Linux scheduling and Python
    callbacks cannot guarantee capture of every transition at high edge rates.
    Use an RP2040 PIO, MCU timer, kernel counter, or dedicated counter backend
    for production AS5304/AS5306 odometry.

    The backend initializes both inputs and always detaches its callbacks on
    close. It closes the inputs only when ``owns_inputs`` is true.
    """

    def __init__(
        self,
        *,
        a_input: DigitalEdgeInputABC,
        b_input: DigitalEdgeInputABC,
        decode_mode: QuadratureDecodeMode = QuadratureDecodeMode.X4,
        owns_inputs: bool = True,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not isinstance(a_input, DigitalEdgeInputABC):
            raise TypeError("a_input must implement DigitalEdgeInputABC")
        if not isinstance(b_input, DigitalEdgeInputABC):
            raise TypeError("b_input must implement DigitalEdgeInputABC")
        if a_input is b_input:
            raise ValueError("a_input and b_input must be different inputs")
        if not isinstance(decode_mode, QuadratureDecodeMode):
            raise TypeError("decode_mode must be a QuadratureDecodeMode")
        if not isinstance(owns_inputs, bool):
            raise TypeError("owns_inputs must be a bool")
        self._a_input = a_input
        self._b_input = b_input
        self._owns_inputs = owns_inputs
        self._decoder = QuadratureDecoder(
            decode_mode=decode_mode,
            monotonic_ns=monotonic_ns,
        )
        self._capture_errors = 0
        self._initialized = False
        self._closed = False
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._closed:
                raise EncoderClosedError("GPIOQuadratureCounterBackend is closed")
            if self._initialized:
                return
            try:
                self._a_input.initialize()
                self._b_input.initialize()
                self._a_input.set_edge_callback(self._handle_edge)
                self._b_input.set_edge_callback(self._handle_edge)
                self._decoder.update(self._a_input.read(), self._b_input.read())
            except Exception as error:
                self._detach_callbacks()
                if self._owns_inputs:
                    self._close_inputs_best_effort()
                raise EncoderBackendError(
                    "failed to initialize GPIO quadrature capture"
                ) from error
            self._initialized = True

    def read_snapshot(self) -> QuadratureCounterSnapshot:
        with self._lock:
            self._require_initialized()
            snapshot = self._decoder.read_snapshot()
            return QuadratureCounterSnapshot(
                count=snapshot.count,
                timestamp_monotonic_ns=snapshot.timestamp_monotonic_ns,
                invalid_transitions=(
                    snapshot.invalid_transitions + self._capture_errors
                ),
            )

    def reset(self, count: int = 0) -> None:
        with self._lock:
            self._require_initialized()
            self._decoder.reset(count)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            callback_error = self._detach_callbacks()
            close_error = (
                self._close_inputs_best_effort() if self._owns_inputs else None
            )
            error = callback_error or close_error
            if error is not None:
                raise EncoderBackendError(
                    "failed to close GPIO quadrature capture"
                ) from error

    def _handle_edge(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._decoder.update(self._a_input.read(), self._b_input.read())
            except Exception:
                self._capture_errors += 1
                _log.warning("failed to sample quadrature A/B state", exc_info=True)

    def _require_initialized(self) -> None:
        if self._closed:
            raise EncoderClosedError("GPIOQuadratureCounterBackend is closed")
        if not self._initialized:
            raise EncoderNotInitializedError(
                "call initialize() before reading the GPIO quadrature counter"
            )

    def _detach_callbacks(self) -> Exception | None:
        first_error: Exception | None = None
        for edge_input in (self._a_input, self._b_input):
            try:
                edge_input.set_edge_callback(None)
            except Exception as error:
                first_error = first_error or error
        return first_error

    def _close_inputs_best_effort(self) -> Exception | None:
        first_error: Exception | None = None
        for edge_input in (self._a_input, self._b_input):
            try:
                edge_input.close()
            except Exception as error:
                first_error = first_error or error
        return first_error


__all__ = ["GPIOQuadratureCounterBackend"]
