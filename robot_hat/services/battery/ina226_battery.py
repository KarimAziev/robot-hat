from typing import Optional

from robot_hat.data_types.bus import BusType
from robot_hat.drivers.adc.INA226 import INA226, INA226Config
from robot_hat.interfaces.battery_abc import BatteryABC


class Battery(INA226, BatteryABC):
    """
    Battery helper built on top of the INA226 I2C sensor driver.
    """

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x40,
        config: Optional[INA226Config] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the Battery object.
        """
        super().__init__(bus=bus, address=address, config=config, *args, **kwargs)

    def get_battery_voltage(self) -> float:
        """
        Get the battery voltage in volts.

        Combines bus voltage (V) and shunt voltage (mV) and returns a rounded
        value in volts.
        """
        bus_voltage = self.get_bus_voltage_v()
        shunt_voltage_v = self.get_shunt_voltage_mv() / 1000.0

        measured_voltage = bus_voltage + shunt_voltage_v
        return round(measured_voltage, 2)

    def close(self) -> None:
        """Close underlying resources (SMBus) if owned."""
        super().close()
