import logging
from typing import List, Optional, Union

from robot_hat.data_types import BatteryMetrics
from robot_hat.drivers.adc.sunfounder_adc import ADC, ADC_DEFAULT_ADDRESSES
from robot_hat.interfaces.battery_abc import BatteryABC

logger = logging.getLogger(__name__)


class Battery(ADC, BatteryABC):
    """
    A class to manage battery-specific readings using the ADC.

    This class extends the ADC functionality and adds battery-specific logic, such as
    scaling the voltage to 10V systems (e.g., common in battery applications).
    """

    def __init__(
        self,
        channel: Union[str, int] = "A4",
        address: Union[int, List[int]] = ADC_DEFAULT_ADDRESSES,
        *args,
        current_channel: Optional[Union[str, int]] = None,
        sense_resistance_ohms: Optional[float] = None,
        **kwargs,
    ) -> None:
        """
        Initialize the Battery object.

        Args:
            `channel`: ADC channel connected to the battery.
            `address`: The address or list of addresses of I2C devices.
            `current_channel`: Optional ADC channel that measures the voltage drop
                across a shunt resistor for current sensing.
            `sense_resistance_ohms`: Resistance value (in ohms) of the shunt used
                for current sensing.
        """
        super().__init__(channel, address, *args, **kwargs)

        if (current_channel is None) != (sense_resistance_ohms is None):
            raise ValueError(
                "current_channel and sense_resistance_ohms must both be provided "
                "to enable current readings"
            )

        if sense_resistance_ohms is not None and sense_resistance_ohms <= 0:
            raise ValueError("sense_resistance_ohms must be positive")

        self._sense_resistance_ohms = sense_resistance_ohms
        self._current_channel = current_channel
        if current_channel is not None:
            current_index = self._normalize_channel(current_channel)
            if current_index == self._channel_index:
                logger.warning(
                    "Current channel %s matches voltage channel; current readings "
                    "will mirror the scaled battery voltage",
                    current_channel,
                )
            self._current_channel_index = current_index
        else:
            self._current_channel_index = None

    def get_battery_voltage(self) -> float:
        """
        Read and scale ADC voltage readings to a 0-10V system.

        Returns:
            float: The scaled battery voltage in volts.
        """
        voltage = self.read_voltage()

        scaled_voltage = round(voltage * 3, 2)  # Scale the 0-3.3V reading to 0-10V
        logger.debug("Battery voltage (scaled to 0-10V): %sV", scaled_voltage)
        return scaled_voltage

    def get_battery_current(self) -> float:
        """Return the battery current in amps if configured."""
        if self._current_channel_index is None or self._sense_resistance_ohms is None:
            raise NotImplementedError(
                "Sunfounder ADC only exposes voltage by default; provide "
                "current_channel and sense_resistance_ohms to enable current readings"
            )

        shunt_voltage = self.read_voltage_channel(self._current_channel_index)
        current = shunt_voltage / self._sense_resistance_ohms
        rounded = round(current, 2)
        logger.debug(
            "Battery current (channel %s, %.4f Ω): %.2fA",
            self._current_channel,
            self._sense_resistance_ohms,
            rounded,
        )
        return rounded

    def get_battery_metrics(self) -> BatteryMetrics:
        """Return both voltage and current readings."""
        return BatteryMetrics(
            voltage=self.get_battery_voltage(),
            current=self.get_battery_current(),
        )
