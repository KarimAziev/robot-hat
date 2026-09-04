import math
from dataclasses import dataclass
from typing import Literal


LSM9DS1AccelerometerRangeG = Literal[2, 4, 8, 16]
LSM9DS1GyroscopeRangeDPS = Literal[245, 500, 2000]
LSM9DS1OutputDataRateHz = Literal[119, 238, 476, 952]


_OUTPUT_DATA_RATE_CODES = {119: 0x03, 238: 0x04, 476: 0x05, 952: 0x06}
_ACCELEROMETER_RANGE_CODES = {2: 0x00, 4: 0x02, 8: 0x03, 16: 0x01}
_ACCELEROMETER_MG_PER_LSB = {2: 0.061, 4: 0.122, 8: 0.244, 16: 0.732}
_GYROSCOPE_RANGE_CODES = {245: 0x00, 500: 0x01, 2000: 0x03}
_GYROSCOPE_MDPS_PER_LSB = {245: 8.75, 500: 17.5, 2000: 70.0}


@dataclass(frozen=True)
class LSM9DS1Config:
    """Full-scale ranges and shared output rate for an LSM9DS1 A/G die."""

    accelerometer_range_g: LSM9DS1AccelerometerRangeG = 2
    gyroscope_range_dps: LSM9DS1GyroscopeRangeDPS = 245
    output_data_rate_hz: LSM9DS1OutputDataRateHz = 119

    def __post_init__(self) -> None:
        if self.accelerometer_range_g not in _ACCELEROMETER_RANGE_CODES:
            raise ValueError("accelerometer_range_g must be 2, 4, 8, or 16")
        if self.gyroscope_range_dps not in _GYROSCOPE_RANGE_CODES:
            raise ValueError("gyroscope_range_dps must be 245, 500, or 2000")
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError("output_data_rate_hz must be 119, 238, 476, or 952")

    @property
    def accelerometer_control_register(self) -> int:
        return (
            _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 5
            | _ACCELEROMETER_RANGE_CODES[self.accelerometer_range_g] << 3
        )

    @property
    def gyroscope_control_register(self) -> int:
        return (
            _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 5
            | _GYROSCOPE_RANGE_CODES[self.gyroscope_range_dps] << 3
        )

    @property
    def accelerometer_mps2_per_lsb(self) -> float:
        return _ACCELEROMETER_MG_PER_LSB[self.accelerometer_range_g] * 9.80665 / 1000.0

    @property
    def gyroscope_radps_per_lsb(self) -> float:
        return _GYROSCOPE_MDPS_PER_LSB[self.gyroscope_range_dps] * math.pi / 180_000.0


__all__ = [
    "LSM9DS1AccelerometerRangeG",
    "LSM9DS1Config",
    "LSM9DS1GyroscopeRangeDPS",
    "LSM9DS1OutputDataRateHz",
]
