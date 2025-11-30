from dataclasses import dataclass


@dataclass(frozen=True)
class BatteryMetrics:
    """Aggregated battery measurements."""

    voltage: float
    current: float

    def __iter__(self):
        yield from (self.voltage, self.current)
