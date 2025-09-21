from typing import Optional

from robot_hat.data_types.bus import BusType
from robot_hat.drivers.adc.INA219 import INA219, INA219Config
from robot_hat.interfaces.battery_abc import BatteryABC


class Battery(INA219, BatteryABC):
    """
    Battery helper built on top of the INA219 I2C sensor driver.

    This class provides battery-specific convenience methods while reusing the
    INA219 low-level driver. It is intended for use with battery monitoring
    modules that expose the INA219 (for example Waveshare UPS_Module_3S
    (UPS_Module_3S (https://www.waveshare.com/wiki/UPS_Module_3S))).

    Note:
    - This class does not change INA219 calibration behavior; use INA219Config
      (or INA219Config.from_shunt()) to select calibration parameters
      appropriate for your shunt resistor and expected current.
    """

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x41,
        config: Optional[INA219Config] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the Battery object.
        """
        super().__init__(
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
