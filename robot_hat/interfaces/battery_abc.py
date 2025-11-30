from abc import ABC, abstractmethod

from robot_hat.data_types import BatteryMetrics


class BatteryABC(ABC):
    @abstractmethod
    def get_battery_current(self) -> float:
        """
        Get the battery current in amps.
        """
        pass

    @abstractmethod
    def get_battery_voltage(self) -> float:
        """
        Get the battery voltage in volts.
        """
        pass

    @abstractmethod
    def get_battery_metrics(self) -> BatteryMetrics:
        """Return both voltage and current readings as a single payload."""
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the underlying resources.
        """
        pass
