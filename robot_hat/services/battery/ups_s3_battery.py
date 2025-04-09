from typing import Optional, Union

from smbus2 import SMBus

from robot_hat.drivers.adc.INA219 import INA219, INA219Config
from robot_hat.services.battery.battery_abc import BatteryABC
from robot_hat.smbus_singleton import SMBus as SMBusSingleton


class Battery(INA219, BatteryABC):
    """
    A class to manage battery-specific readings using the UPS Module 3S.

    https://www.waveshare.com/wiki/UPS_Module_3S
    """

    def __init__(
        self,
        bus_num: int = 1,
        address: int = 0x41,
        config: Optional[INA219Config] = None,
        bus: Union[SMBusSingleton, SMBus, None] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the Battery object.
        """
        super().__init__(
            bus_num=bus_num,
            address=address,
            config=config,
            bus=bus,
            *args,
            **kwargs,
        )

    def get_battery_voltage(self) -> float:
        """
        Get the battery voltage in volts.
        """
        bus_voltage = self.get_bus_voltage_v()
        shunt_voltage = self.get_shunt_voltage_mv() / 1000.0

        measured_voltage = bus_voltage + shunt_voltage

        scaled_voltage = round(measured_voltage, 2)

        return scaled_voltage
