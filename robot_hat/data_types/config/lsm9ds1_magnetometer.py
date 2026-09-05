from dataclasses import dataclass
from typing import Literal, TypeAlias


LSM9DS1MagneticFieldRangeGauss = Literal[4, 8, 12, 16]
LSM9DS1MagnetometerOutputDataRateHz: TypeAlias = float
LSM9DS1MagnetometerPerformanceMode = Literal["low", "medium", "high", "ultra_high"]

_OUTPUT_DATA_RATE_CODES = {
    0.625: 0x00,
    1.25: 0x01,
    2.5: 0x02,
    5.0: 0x03,
    10.0: 0x04,
    20.0: 0x05,
    40.0: 0x06,
    80.0: 0x07,
}
_RANGE_CODES = {4: 0x00, 8: 0x01, 12: 0x02, 16: 0x03}
_MILLIGAUSS_PER_LSB = {4: 0.14, 8: 0.29, 12: 0.43, 16: 0.58}
_PERFORMANCE_CODES = {"low": 0x00, "medium": 0x01, "high": 0x02, "ultra_high": 0x03}


@dataclass(frozen=True)
class LSM9DS1MagnetometerConfig:
    """Range, output rate, and conversion mode for the LSM9DS1 magnetic die."""

    magnetic_field_range_gauss: LSM9DS1MagneticFieldRangeGauss = 4
    output_data_rate_hz: LSM9DS1MagnetometerOutputDataRateHz = 20.0
    performance_mode: LSM9DS1MagnetometerPerformanceMode = "ultra_high"

    def __post_init__(self) -> None:
        if self.magnetic_field_range_gauss not in _RANGE_CODES:
            raise ValueError("magnetic_field_range_gauss must be 4, 8, 12, or 16")
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError("unsupported LSM9DS1 magnetometer output_data_rate_hz")
        if self.performance_mode not in _PERFORMANCE_CODES:
            raise ValueError("unsupported LSM9DS1 magnetometer performance_mode")

    @property
    def control_register_1(self) -> int:
        # Enable temperature compensation and use the same XY performance mode.
        return (
            0x80
            | _PERFORMANCE_CODES[self.performance_mode] << 5
            | _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 2
        )

    @property
    def control_register_2(self) -> int:
        return _RANGE_CODES[self.magnetic_field_range_gauss] << 5

    @property
    def control_register_4(self) -> int:
        return _PERFORMANCE_CODES[self.performance_mode] << 2

    @property
    def tesla_per_lsb(self) -> float:
        return _MILLIGAUSS_PER_LSB[self.magnetic_field_range_gauss] * 1e-7


__all__ = [
    "LSM9DS1MagneticFieldRangeGauss",
    "LSM9DS1MagnetometerConfig",
    "LSM9DS1MagnetometerOutputDataRateHz",
    "LSM9DS1MagnetometerPerformanceMode",
]
