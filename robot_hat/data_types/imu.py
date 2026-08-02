import math
from dataclasses import dataclass
from typing import Tuple


Vector3 = Tuple[float, float, float]
RawVector3 = Tuple[int, int, int]


def _validate_vector(name: str, value: Vector3) -> None:
    if len(value) != 3:
        raise ValueError(f"{name} must contain exactly three axes")
    if not all(math.isfinite(axis) for axis in value):
        raise ValueError(f"{name} axes must be finite")


@dataclass(frozen=True)
class IMUSample:
    """One six-axis inertial observation in SI units.

    Axes use the concrete sensor driver's documented local frame. Consumers are
    responsible for applying the rigid transform from that frame to the robot
    base frame.
    """

    acceleration_mps2: Vector3
    angular_velocity_radps: Vector3
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        _validate_vector("acceleration_mps2", self.acceleration_mps2)
        _validate_vector("angular_velocity_radps", self.angular_velocity_radps)
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


@dataclass(frozen=True)
class RawIMUSample:
    """Unscaled signed sensor counts for diagnostics and calibration tools."""

    accelerometer_counts: RawVector3
    gyroscope_counts: RawVector3
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        if len(self.accelerometer_counts) != 3:
            raise ValueError("accelerometer_counts must contain exactly three axes")
        if len(self.gyroscope_counts) != 3:
            raise ValueError("gyroscope_counts must contain exactly three axes")
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


__all__ = ["IMUSample", "RawIMUSample", "RawVector3", "Vector3"]
