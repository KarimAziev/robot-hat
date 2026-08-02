"""Vendor-neutral quadrature counter data types and resolution helpers."""

from dataclasses import dataclass
from enum import Enum


class QuadratureDecodeMode(Enum):
    """Number of reported counts per complete A/B electrical cycle.

    ``X1`` reports one count per complete cycle, ``X2`` reports one count per
    half-cycle, and ``X4`` reports every legal Gray-code state transition.
    """

    X1 = 1
    X2 = 2
    X4 = 4


@dataclass(frozen=True)
class QuadratureCounterSnapshot:
    """Atomic snapshot of one signed cumulative quadrature counter.

    ``count`` uses the backend's configured :class:`QuadratureDecodeMode`.
    ``timestamp_monotonic_ns`` is an observation time from
    :func:`time.monotonic_ns`, never wall-clock time. Diagnostics accumulate
    from backend construction or initialization as documented by the backend.
    """

    count: int
    timestamp_monotonic_ns: int
    invalid_transitions: int = 0

    def __post_init__(self) -> None:
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")
        if self.invalid_transitions < 0:
            raise ValueError("invalid_transitions must be non-negative")


def as530x_counts_per_revolution(
    pole_pairs: int,
    decode_mode: QuadratureDecodeMode = QuadratureDecodeMode.X4,
) -> int:
    """Return AS5304/AS5306 counts per mechanical ring revolution.

    AS5304 and AS5306 produce 40 A/B periods per magnetic pole pair. Therefore
    the count is ``40 * decode_mode.value * pole_pairs``.
    """

    if isinstance(pole_pairs, bool) or not isinstance(pole_pairs, int):
        raise TypeError("pole_pairs must be an integer")
    if pole_pairs <= 0:
        raise ValueError("pole_pairs must be positive")
    if not isinstance(decode_mode, QuadratureDecodeMode):
        raise TypeError("decode_mode must be a QuadratureDecodeMode")
    return 40 * decode_mode.value * pole_pairs


__all__ = [
    "QuadratureCounterSnapshot",
    "QuadratureDecodeMode",
    "as530x_counts_per_revolution",
]
