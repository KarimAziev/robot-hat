import math
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentalSample:
    """Timestamped environmental measurements exposed by one physical sensor.

    A concrete device reports only the quantities it can measure. Pressure is
    expressed in pascals; relative humidity is expressed as a percentage.
    """

    timestamp_monotonic_ns: int
    temperature_c: float | None = None
    relative_humidity_percent: float | None = None
    pressure_pa: float | None = None

    def __post_init__(self) -> None:
        values = (
            self.temperature_c,
            self.relative_humidity_percent,
            self.pressure_pa,
        )
        if all(value is None for value in values):
            raise ValueError("an environmental sample must contain a measurement")
        if any(value is not None and not math.isfinite(value) for value in values):
            raise ValueError("environmental measurements must be finite")
        if self.relative_humidity_percent is not None and not (
            0.0 <= self.relative_humidity_percent <= 100.0
        ):
            raise ValueError("relative_humidity_percent must be between 0 and 100")
        if self.pressure_pa is not None and self.pressure_pa < 0.0:
            raise ValueError("pressure_pa must be non-negative")
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


__all__ = ["EnvironmentalSample"]
