from dataclasses import dataclass, field
from enum import IntEnum


class AveragingCount(IntEnum):
    COUNT_1 = 0
    COUNT_4 = 1
    COUNT_16 = 2
    COUNT_64 = 3
    COUNT_128 = 4
    COUNT_256 = 5
    COUNT_512 = 6
    COUNT_1024 = 7


class ConversionTime(IntEnum):
    TIME_140_US = 0
    TIME_204_US = 1
    TIME_332_US = 2
    TIME_588_US = 3
    TIME_1_1_MS = 4
    TIME_2_116_MS = 5
    TIME_4_156_MS = 6
    TIME_8_244_MS = 7


class Mode(IntEnum):
    SHUTDOWN = 0
    CURRENT_TRIGGERED = 1
    BUS_TRIGGERED = 2
    SHUNT_AND_BUS_TRIGGERED = 3
    POWER_DOWN_4 = 4  # reserved in datasheet; kept for completeness
    CURRENT_CONTINUOUS = 5
    BUS_CONTINUOUS = 6
    CONTINUOUS = 7


@dataclass
class INA260Config:
    """
    High-level configuration bundle for the INA260 sensor.

    The INA260 integrates a 2 mΩ shunt resistor and exposes a single configuration
    register controlling averaging and conversion timing. Alerts are optional and
    disabled by default.
    """

    averaging_count: AveragingCount = field(
        default=AveragingCount.COUNT_4,
        metadata={"desc": "Rolling average window for conversions"},
    )
    voltage_conversion_time: ConversionTime = field(
        default=ConversionTime.TIME_1_1_MS,
        metadata={"desc": "Conversion time for bus voltage measurements"},
    )
    current_conversion_time: ConversionTime = field(
        default=ConversionTime.TIME_1_1_MS,
        metadata={"desc": "Conversion time for current measurements"},
    )
    mode: Mode = field(
        default=Mode.CONTINUOUS,
        metadata={"desc": "Operating mode"},
    )
    alert_mask: int = field(
        default=0,
        metadata={"desc": "Mask/enable register (16-bit)"},
    )
    alert_limit: int = field(
        default=0,
        metadata={"desc": "Alert limit register (16-bit)"},
    )
    shunt_resistance_ohms: float = field(
        default=0.002,
        metadata={
            "units": "ohm",
            "desc": "Effective shunt resistance used to derive shunt voltage",
        },
    )
    reset_on_init: bool = field(
        default=False,
        metadata={"desc": "Set RESET bit when applying configuration"},
    )

    BUS_VOLTAGE_LSB_V = 0.00125
    CURRENT_LSB_MA = 1.25
    POWER_LSB_MW = 10.0

    def __post_init__(self) -> None:
        if not (0.0 < self.shunt_resistance_ohms <= 0.01):
            raise ValueError("shunt_resistance_ohms should be in the range (0, 0.01]")
        if not (0 <= self.alert_mask <= 0xFFFF):
            raise ValueError("alert_mask must fit within 16 bits")
        if not (0 <= self.alert_limit <= 0xFFFF):
            raise ValueError("alert_limit must fit within 16 bits")
        if not isinstance(self.mode, Mode):
            raise ValueError("Invalid operating mode specified")

    def to_register_value(self) -> int:
        """Serialize configuration bits for the CONFIG register."""
        value = 0
        if self.reset_on_init:
            value |= 1 << 15
        value |= (int(self.averaging_count) & 0x07) << 9
        value |= (int(self.voltage_conversion_time) & 0x07) << 6
        value |= (int(self.current_conversion_time) & 0x07) << 3
        value |= int(self.mode) & 0x07
        return value

    def copy_with(
        self,
        *,
        averaging_count: AveragingCount | None = None,
        voltage_conversion_time: ConversionTime | None = None,
        current_conversion_time: ConversionTime | None = None,
        mode: Mode | None = None,
        alert_mask: int | None = None,
        alert_limit: int | None = None,
        shunt_resistance_ohms: float | None = None,
        reset_on_init: bool | None = None,
    ) -> "INA260Config":
        """Convenience helper for immutably tweaking configuration values."""
        return INA260Config(
            averaging_count=(
                self.averaging_count if averaging_count is None else averaging_count
            ),
            voltage_conversion_time=(
                self.voltage_conversion_time
                if voltage_conversion_time is None
                else voltage_conversion_time
            ),
            current_conversion_time=(
                self.current_conversion_time
                if current_conversion_time is None
                else current_conversion_time
            ),
            mode=self.mode if mode is None else mode,
            alert_mask=self.alert_mask if alert_mask is None else alert_mask,
            alert_limit=self.alert_limit if alert_limit is None else alert_limit,
            shunt_resistance_ohms=(
                self.shunt_resistance_ohms
                if shunt_resistance_ohms is None
                else shunt_resistance_ohms
            ),
            reset_on_init=(
                self.reset_on_init if reset_on_init is None else reset_on_init
            ),
        )
