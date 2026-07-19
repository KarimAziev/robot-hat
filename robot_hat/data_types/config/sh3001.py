from dataclasses import dataclass
from typing import Literal


AccelerometerRangeG = Literal[2, 4, 8, 16]
GyroscopeRangeDPS = Literal[125, 250, 500, 1000, 2000]


_ACCELEROMETER_RANGE_REGISTERS = {16: 0x02, 8: 0x03, 4: 0x04, 2: 0x05}
_ACCELEROMETER_LSB_PER_G = {2: 16384.0, 4: 8192.0, 8: 4096.0, 16: 2048.0}
_GYROSCOPE_RANGE_REGISTERS = {
    125: 0x02,
    250: 0x03,
    500: 0x04,
    1000: 0x05,
    2000: 0x06,
}
_GYROSCOPE_LSB_PER_DPS = {
    125: 262.0,
    250: 131.0,
    500: 65.5,
    1000: 32.8,
    2000: 16.4,
}


@dataclass(frozen=True)
class SH3001Config:
    """Physical ranges used to configure and scale an SH3001."""

    accelerometer_range_g: AccelerometerRangeG = 2
    gyroscope_range_dps: GyroscopeRangeDPS = 2000

    def __post_init__(self) -> None:
        if self.accelerometer_range_g not in _ACCELEROMETER_RANGE_REGISTERS:
            raise ValueError("accelerometer_range_g must be 2, 4, 8, or 16")
        if self.gyroscope_range_dps not in _GYROSCOPE_RANGE_REGISTERS:
            raise ValueError("gyroscope_range_dps must be 125, 250, 500, 1000, or 2000")

    @property
    def accelerometer_range_register(self) -> int:
        return _ACCELEROMETER_RANGE_REGISTERS[self.accelerometer_range_g]

    @property
    def accelerometer_lsb_per_g(self) -> float:
        return _ACCELEROMETER_LSB_PER_G[self.accelerometer_range_g]

    @property
    def gyroscope_range_register(self) -> int:
        return _GYROSCOPE_RANGE_REGISTERS[self.gyroscope_range_dps]

    @property
    def gyroscope_lsb_per_dps(self) -> float:
        return _GYROSCOPE_LSB_PER_DPS[self.gyroscope_range_dps]


__all__ = ["AccelerometerRangeG", "GyroscopeRangeDPS", "SH3001Config"]
