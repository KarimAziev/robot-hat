"""Factory helpers for constructing BatteryABC implementations."""

from __future__ import annotations

import logging
from typing import Any

from robot_hat.data_types.config.battery import (
    BatteryConfigType,
    INA219BatteryConfig,
    INA226BatteryConfig,
    INA260BatteryConfig,
    SunfounderBatteryConfig,
)
from robot_hat.interfaces.battery_abc import BatteryABC
from robot_hat.services.battery.ina219_battery import Battery as INA219Battery
from robot_hat.services.battery.ina226_battery import Battery as INA226Battery
from robot_hat.services.battery.ina260_battery import Battery as INA260Battery
from robot_hat.services.battery.sunfounder_battery import Battery as SunfounderBattery

_log = logging.getLogger(__name__)


class BatteryFactory:
    """Create battery helper instances from configuration dataclasses."""

    @classmethod
    def create_battery(
        cls,
        config: BatteryConfigType,
        **kwargs: Any,
    ) -> BatteryABC:
        """Instantiate a battery helper based on the supplied configuration."""
        if isinstance(config, INA219BatteryConfig):
            _log.debug(
                "Creating INA219 battery helper on bus %s address 0x%02X",
                config.bus,
                config.address,
            )
            return INA219Battery(
                bus=config.bus,
                address=config.address,
                config=config.sensor_config,
                **kwargs,
            )
        if isinstance(config, INA226BatteryConfig):
            _log.debug(
                "Creating INA226 battery helper on bus %s address 0x%02X",
                config.bus,
                config.address,
            )
            return INA226Battery(
                bus=config.bus,
                address=config.address,
                config=config.sensor_config,
                **kwargs,
            )
        if isinstance(config, INA260BatteryConfig):
            _log.debug(
                "Creating INA260 battery helper on bus %s address 0x%02X",
                config.bus,
                config.address,
            )
            return INA260Battery(
                bus=config.bus,
                address=config.address,
                config=config.sensor_config,
                **kwargs,
            )
        if isinstance(config, SunfounderBatteryConfig):
            _log.debug(
                "Creating Sunfounder battery helper channel %s address %s",
                config.channel,
                config.address,
            )
            return SunfounderBattery(
                channel=config.channel,
                address=config.address,
                **kwargs,
            )

        raise TypeError(f"Unsupported battery config type: {type(config).__name__}")
