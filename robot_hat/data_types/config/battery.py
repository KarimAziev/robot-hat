from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.ina219 import INA219Config
from robot_hat.data_types.config.ina226 import INA226Config
from robot_hat.data_types.config.ina260 import INA260Config
from robot_hat.drivers.adc.sunfounder_adc import ADC_DEFAULT_ADDRESSES


@dataclass
class INA219BatteryConfig:
    """Configuration for creating an INA219-based battery helper."""

    bus: BusType = 1
    address: int = 0x41
    sensor_config: Optional[INA219Config] = None


@dataclass
class INA226BatteryConfig:
    """Configuration for creating an INA226-based battery helper."""

    bus: BusType = 1
    address: int = 0x40
    sensor_config: Optional[INA226Config] = None


@dataclass
class INA260BatteryConfig:
    """Configuration for creating an INA260-based battery helper."""

    bus: BusType = 1
    address: int = 0x40
    sensor_config: Optional[INA260Config] = None


@dataclass
class SunfounderBatteryConfig:
    """Configuration for the legacy Sunfounder ADC-backed battery helper."""

    channel: Union[str, int] = "A4"
    address: Union[int, List[int]] = field(
        default_factory=lambda: ADC_DEFAULT_ADDRESSES.copy()
    )


BatteryConfigType = Union[
    INA219BatteryConfig,
    INA226BatteryConfig,
    INA260BatteryConfig,
    SunfounderBatteryConfig,
]
