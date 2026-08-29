"""Pure, thread-safe A/B Gray-code quadrature decoder."""

import time
from threading import RLock
from typing import Callable, Final

from robot_hat.data_types.quadrature import (
    QuadratureCounterSnapshot,
    QuadratureDecodeMode,
)


# Indexed by ``(previous_state << 2) | current_state``. The positive sequence is
# 00 -> 01 -> 11 -> 10 -> 00. Entries with both bits changed are invalid and
# represented separately so repeated states remain ordinary zero movement.
_TRANSITION_DELTAS: Final[tuple[int, ...]] = (
    0,
    1,
    -1,
    0,
    -1,
    0,
    0,
    1,
    1,
    0,
    0,
    -1,
    0,
    -1,
    1,
    0,
)


class QuadratureDecoder:
    """Decode sampled A/B states into a signed cumulative count.

    The positive Gray-code sequence is ``00 -> 01 -> 11 -> 10 -> 00``.
    ``X4`` counts every legal transition, ``X2`` counts each two net legal
    transitions, and ``X1`` counts each four net legal transitions (one complete
    A/B electrical cycle). Partial movement is retained so reversals cancel it.

    The first state establishes phase without adding a count. A two-bit change
    is diagnosed as invalid, re-establishes phase at the new state, and discards
    any ambiguous partial-cycle movement. Repeated states are harmless. Reset
    preserves the established electrical state but clears partial movement.

    Direction configuration intentionally does not live here. The public
    :class:`~robot_hat.sensors.encoder.quadrature_encoder.QuadratureEncoder`
    applies inversion once, independent of the chosen hardware backend.
    """

    def __init__(
        self,
        *,
        decode_mode: QuadratureDecodeMode = QuadratureDecodeMode.X4,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if not isinstance(decode_mode, QuadratureDecodeMode):
            raise TypeError("decode_mode must be a QuadratureDecodeMode")
        self._decode_mode = decode_mode
        self._monotonic_ns = monotonic_ns
        self._lock = RLock()
        self._count = 0
        self._partial_transitions = 0
        self._invalid_transitions = 0
        self._previous_state: int | None = None

    @property
    def decode_mode(self) -> QuadratureDecodeMode:
        return self._decode_mode

    def update(self, a: bool, b: bool) -> None:
        """Observe one logical A/B state atomically."""

        if not isinstance(a, bool) or not isinstance(b, bool):
            raise TypeError("a and b must be bool values")
        state = (int(a) << 1) | int(b)
        with self._lock:
            previous_state = self._previous_state
            self._previous_state = state
            if previous_state is None or previous_state == state:
                return
            if previous_state ^ state == 0b11:
                self._invalid_transitions += 1
                self._partial_transitions = 0
                return

            delta = _TRANSITION_DELTAS[(previous_state << 2) | state]
            self._partial_transitions += delta
            transitions_per_count = 4 // self._decode_mode.value
            if self._partial_transitions >= transitions_per_count:
                self._count += 1
                self._partial_transitions -= transitions_per_count
            elif self._partial_transitions <= -transitions_per_count:
                self._count -= 1
                self._partial_transitions += transitions_per_count

    def read_snapshot(self) -> QuadratureCounterSnapshot:
        """Return an atomic snapshot timestamped by the injected monotonic clock."""

        with self._lock:
            return QuadratureCounterSnapshot(
                count=self._count,
                timestamp_monotonic_ns=self._monotonic_ns(),
                invalid_transitions=self._invalid_transitions,
            )

    def reset(self, count: int = 0) -> None:
        """Set the count while retaining the current A/B phase baseline."""

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer")
        with self._lock:
            self._count = count
            self._partial_transitions = 0


__all__ = ["QuadratureDecoder"]
