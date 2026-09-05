from abc import ABC, abstractmethod

from robot_hat.data_types.environment import EnvironmentalSample


class EnvironmentalSensorABC(ABC):
    """Vendor-neutral synchronous environmental-sensor interface."""

    @abstractmethod
    def initialize(self) -> None:
        """Validate and configure the physical sensor."""

    @abstractmethod
    def read_sample(self) -> EnvironmentalSample:
        """Read one timestamped sample in documented engineering units."""

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the implementation."""


__all__ = ["EnvironmentalSensorABC"]
