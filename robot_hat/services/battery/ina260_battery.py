from typing import Optional

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.ina260 import INA260Config
from robot_hat.drivers.adc.INA260 import INA260
from robot_hat.interfaces.battery_abc import BatteryABC


class Battery(INA260, BatteryABC):
    """Battery helper built on top of the INA260 driver."""

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x40,
        config: Optional[INA260Config] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(bus=bus, address=address, config=config, *args, **kwargs)

    def get_battery_voltage(self) -> float:
        """Estimate pack voltage by combining bus voltage and shunt drop."""
        bus_voltage = self.get_bus_voltage_v()
        shunt_drop_v = self.get_shunt_voltage_mv() / 1000.0
        return round(bus_voltage + shunt_drop_v, 2)

    def close(self) -> None:
        super().close()
