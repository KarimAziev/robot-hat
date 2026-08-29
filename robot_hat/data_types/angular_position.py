import math
from dataclasses import dataclass

from robot_hat.data_types.encoder import EncoderHealth


@dataclass(frozen=True)
class AngularPositionSample:
    """One timestamped absolute angular-position observation in degrees."""

    angle_degrees: float
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        if not math.isfinite(self.angle_degrees):
            raise ValueError("angle_degrees must be finite")
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


AngularPositionHealth = EncoderHealth


__all__ = [
    "AngularPositionHealth",
    "AngularPositionSample",
]
