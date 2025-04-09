from abc import ABC, abstractmethod


class BatteryABC(ABC):
    @abstractmethod
    def get_battery_voltage(self) -> float:
        """
        Get the battery voltage in volts.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the underlying resources.
        """
        pass
