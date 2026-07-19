import math
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class LidarHealthStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LidarDeviceInfo:
    """Vendor-neutral identity information for a 2D lidar."""

    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str
    hardware_version: str


@dataclass(frozen=True)
class LidarHealth:
    status: LidarHealthStatus
    error_code: Optional[int] = None

    @property
    def is_usable(self) -> bool:
        return self.status in (LidarHealthStatus.OK, LidarHealthStatus.WARNING)


@dataclass(frozen=True)
class LidarMeasurement:
    """One polar range sample in a counter-clockwise, sensor-local frame."""

    angle_deg: float
    distance_m: float
    quality: int
    start_of_scan: bool
    timestamp: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.angle_deg < 360.0:
            raise ValueError("angle_deg must be in the range [0, 360)")
        if self.distance_m < 0.0:
            raise ValueError("distance_m must be non-negative")
        if not 0 <= self.quality <= 255:
            raise ValueError("quality must be in the range [0, 255]")

    @property
    def is_valid(self) -> bool:
        """Whether this sample contains a non-zero measured range."""

        return self.distance_m > 0.0

    @property
    def x_m(self) -> float:
        return self.distance_m * math.cos(math.radians(self.angle_deg))

    @property
    def y_m(self) -> float:
        return self.distance_m * math.sin(math.radians(self.angle_deg))


@dataclass(frozen=True)
class LidarScan:
    """One complete revolution of ordered lidar measurements."""

    measurements: Tuple[LidarMeasurement, ...]
    started_at: float
    ended_at: float

    def __post_init__(self) -> None:
        if not self.measurements:
            raise ValueError("measurements must not be empty")
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must not precede started_at")

    @property
    def duration_s(self) -> float:
        return self.ended_at - self.started_at

    @property
    def valid_measurements(self) -> Tuple[LidarMeasurement, ...]:
        return tuple(point for point in self.measurements if point.is_valid)

    @property
    def xy_points_m(self) -> Tuple[Tuple[float, float], ...]:
        """Return valid samples as Cartesian points for mapping consumers."""

        return tuple((point.x_m, point.y_m) for point in self.valid_measurements)
