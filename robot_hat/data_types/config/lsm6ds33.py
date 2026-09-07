import math
from dataclasses import dataclass
from typing import Literal


LSM6DS33AccelerometerRangeG = Literal[2, 4, 8, 16]
LSM6DS33GyroscopeRangeDPS = Literal[125, 245, 500, 1000, 2000]
LSM6DS33OutputDataRateHz = Literal[13, 26, 52, 104, 208, 416, 833, 1666]


_OUTPUT_DATA_RATE_CODES = {
    13: 0x01,
    26: 0x02,
    52: 0x03,
    104: 0x04,
    208: 0x05,
    416: 0x06,
    833: 0x07,
    1666: 0x08,
}
_ACCELEROMETER_RANGE_BITS = {2: 0x00, 4: 0x08, 8: 0x0C, 16: 0x04}
_ACCELEROMETER_MG_PER_LSB = {2: 0.061, 4: 0.122, 8: 0.244, 16: 0.488}
_GYROSCOPE_RANGE_BITS = {
    125: 0x02,
    245: 0x00,
    500: 0x04,
    1000: 0x08,
    2000: 0x0C,
}
_GYROSCOPE_MDPS_PER_LSB = {
    125: 4.375,
    245: 8.75,
    500: 17.5,
    1000: 35.0,
    2000: 70.0,
}


@dataclass(frozen=True)
class LSM6DS33Config:
    """Full-scale ranges and shared output rate for an LSM6DS33."""

    accelerometer_range_g: LSM6DS33AccelerometerRangeG = 2
    gyroscope_range_dps: LSM6DS33GyroscopeRangeDPS = 245
    output_data_rate_hz: LSM6DS33OutputDataRateHz = 104

    def __post_init__(self) -> None:
        if self.accelerometer_range_g not in _ACCELEROMETER_RANGE_BITS:
            raise ValueError("accelerometer_range_g must be 2, 4, 8, or 16")
        if self.gyroscope_range_dps not in _GYROSCOPE_RANGE_BITS:
            raise ValueError("gyroscope_range_dps must be 125, 245, 500, 1000, or 2000")
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError(
                "output_data_rate_hz must be 13, 26, 52, 104, 208, 416, 833, or 1666"
            )

    @property
    def accelerometer_control_register(self) -> int:
        return (
            _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 4
            | _ACCELEROMETER_RANGE_BITS[self.accelerometer_range_g]
        )

    @property
    def gyroscope_control_register(self) -> int:
        return (
            _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 4
            | _GYROSCOPE_RANGE_BITS[self.gyroscope_range_dps]
        )

    @property
    def accelerometer_mps2_per_lsb(self) -> float:
        return _ACCELEROMETER_MG_PER_LSB[self.accelerometer_range_g] * 9.80665 / 1000

    @property
    def gyroscope_radps_per_lsb(self) -> float:
        return _GYROSCOPE_MDPS_PER_LSB[self.gyroscope_range_dps] * math.pi / 180_000


__all__ = [
    "LSM6DS33AccelerometerRangeG",
    "LSM6DS33Config",
    "LSM6DS33GyroscopeRangeDPS",
    "LSM6DS33OutputDataRateHz",
]
