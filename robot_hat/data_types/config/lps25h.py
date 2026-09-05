from dataclasses import dataclass
from typing import TypeAlias


LPS25HOutputDataRateHz: TypeAlias = float

_OUTPUT_DATA_RATE_CODES = {1.0: 0x01, 7.0: 0x02, 12.5: 0x03, 25.0: 0x04}


@dataclass(frozen=True)
class LPS25HConfig:
    """Output rate for the register-compatible LPS25H/LPS25HB family."""

    output_data_rate_hz: LPS25HOutputDataRateHz = 1.0

    def __post_init__(self) -> None:
        if self.output_data_rate_hz not in _OUTPUT_DATA_RATE_CODES:
            raise ValueError("output_data_rate_hz must be 1, 7, 12.5, or 25")

    @property
    def control_register(self) -> int:
        # PD=1, BDU=1, ODR from the typed configuration.
        return 0x80 | (_OUTPUT_DATA_RATE_CODES[self.output_data_rate_hz] << 4) | 0x04


__all__ = ["LPS25HConfig", "LPS25HOutputDataRateHz"]
