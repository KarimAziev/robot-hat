from dataclasses import dataclass
from typing import Literal, TypeAlias


LIS3MDLMagneticFieldRangeGauss = Literal[4, 8, 12, 16]
LIS3MDLOutputDataRateHz: TypeAlias = float
LIS3MDLPerformanceMode = Literal["low", "medium", "high", "ultra_high"]

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
_LSB_PER_GAUSS = {4: 6842, 8: 3421, 12: 2281, 16: 1711}
_PERFORMANCE_CODES = {"low": 0x00, "medium": 0x01, "high": 0x02, "ultra_high": 0x03}


@dataclass(frozen=True)
class LIS3MDLConfig:
    """Full-scale range, output rate, and performance mode for a LIS3MDL."""

    magnetic_field_range_gauss: LIS3MDLMagneticFieldRangeGauss = 4
    output_data_rate_hz: LIS3MDLOutputDataRateHz = 10.0
    performance_mode: LIS3MDLPerformanceMode = "ultra_high"

    def __post_init__(self) -> None:
        if self.magnetic_field_range_gauss not in _RANGE_CODES:
            raise ValueError("magnetic_field_range_gauss must be 4, 8, 12, or 16")
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError("unsupported LIS3MDL output_data_rate_hz")
        if self.performance_mode not in _PERFORMANCE_CODES:
            raise ValueError("unsupported LIS3MDL performance_mode")

    @property
    def control_register_1(self) -> int:
        return (
            _PERFORMANCE_CODES[self.performance_mode] << 5
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
        return 1e-4 / _LSB_PER_GAUSS[self.magnetic_field_range_gauss]


__all__ = [
    "LIS3MDLConfig",
    "LIS3MDLMagneticFieldRangeGauss",
    "LIS3MDLOutputDataRateHz",
    "LIS3MDLPerformanceMode",
]
