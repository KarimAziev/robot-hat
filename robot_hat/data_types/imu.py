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

    Both vectors use axis order ``(x, y, z)`` in the same right-handed,
    sensor-local frame. Concrete drivers document the positive axis directions
    and normalize hardware axis conventions before constructing this sample.
    Positive angular velocity follows the right-hand rule about each axis.

    ``acceleration_mps2`` is accelerometer specific force in m/s², without
    gravity removal. A stationary sensor with local +Z pointing upward reports
    approximately ``(0, 0, +9.80665)``; ideal free fall reports zero.
    ``angular_velocity_radps`` is angular velocity in rad/s.

    ``timestamp_monotonic_ns`` is the host observation time in nanoseconds,
    using ``time.monotonic_ns()`` or an injected clock with the same semantics.
    It is not Unix time or a guarantee of simultaneous hardware acquisition.
    Compare timestamps only within a shared monotonic clock domain.

    Consumers apply the installation-specific mounting rotation into the robot
    frame and own bias calibration, gravity compensation, and sensor fusion.
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
    """Unscaled signed sensor counts for diagnostics and calibration tools.

    Axis order and signs follow the concrete driver's documented native
    register convention, which may differ from the normalized ``IMUSample``
    frame. The timestamp has the same host monotonic semantics as ``IMUSample``.
    """

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
