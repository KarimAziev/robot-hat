import math
from dataclasses import dataclass
from typing import Tuple


MagneticFieldVector = Tuple[float, float, float]
RawMagneticFieldVector = Tuple[int, int, int]


@dataclass(frozen=True)
class MagnetometerSample:
    """One native-axis magnetic-field observation in teslas."""

    magnetic_field_t: MagneticFieldVector
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        if len(self.magnetic_field_t) != 3:
            raise ValueError("magnetic_field_t must contain exactly three axes")
        if not all(math.isfinite(axis) for axis in self.magnetic_field_t):
            raise ValueError("magnetic_field_t axes must be finite")
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


@dataclass(frozen=True)
class RawMagnetometerSample:
    """Unscaled signed magnetometer counts for diagnostics and calibration."""

    magnetic_field_counts: RawMagneticFieldVector
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        if len(self.magnetic_field_counts) != 3:
            raise ValueError("magnetic_field_counts must contain exactly three axes")
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


__all__ = [
    "MagneticFieldVector",
    "MagnetometerSample",
    "RawMagneticFieldVector",
    "RawMagnetometerSample",
]
