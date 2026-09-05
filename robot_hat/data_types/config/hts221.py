from dataclasses import dataclass
from typing import Literal, TypeAlias


HTS221OutputDataRateHz: TypeAlias = float
HTS221HumidityAverageSamples = Literal[4, 8, 16, 32, 64, 128, 256, 512]
HTS221TemperatureAverageSamples = Literal[2, 4, 8, 16, 32, 64, 128, 256]

_OUTPUT_DATA_RATE_CODES = {1.0: 0x01, 7.0: 0x02, 12.5: 0x03}
_HUMIDITY_AVERAGE_CODES = {
    samples: code for code, samples in enumerate((4, 8, 16, 32, 64, 128, 256, 512))
}
_TEMPERATURE_AVERAGE_CODES = {
    samples: code for code, samples in enumerate((2, 4, 8, 16, 32, 64, 128, 256))
}


@dataclass(frozen=True)
class HTS221Config:
    """Output rate and hardware averaging for an HTS221 sensor."""

    output_data_rate_hz: HTS221OutputDataRateHz = 1.0
    humidity_average_samples: HTS221HumidityAverageSamples = 32
    temperature_average_samples: HTS221TemperatureAverageSamples = 16

    def __post_init__(self) -> None:
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError("output_data_rate_hz must be 1, 7, or 12.5")
        if self.humidity_average_samples not in _HUMIDITY_AVERAGE_CODES:
            raise ValueError("unsupported HTS221 humidity averaging count")
        if self.temperature_average_samples not in _TEMPERATURE_AVERAGE_CODES:
            raise ValueError("unsupported HTS221 temperature averaging count")

    @property
    def control_register(self) -> int:
        # PD=1, BDU=1, ODR from the typed configuration.
        return 0x80 | 0x04 | _OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz]

    @property
    def averaging_register(self) -> int:
        return (
            _TEMPERATURE_AVERAGE_CODES[self.temperature_average_samples] << 3
            | _HUMIDITY_AVERAGE_CODES[self.humidity_average_samples]
        )


__all__ = [
    "HTS221Config",
    "HTS221HumidityAverageSamples",
    "HTS221OutputDataRateHz",
    "HTS221TemperatureAverageSamples",
]
