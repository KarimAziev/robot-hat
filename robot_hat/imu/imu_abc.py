from abc import ABC, abstractmethod
from typing import List, Tuple


class AbstractIMU(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Initialize and configure the sensor. Raise an exception on failure."""
        pass

    @abstractmethod
    def read_sensor_data(self) -> Tuple[List[float], List[float]]:
        """
        Returns a tuple of accelerometer and gyroscope data.
        For example: ([ax, ay, az], [gx, gy, gz])
        """
        pass
