from abc import ABC, abstractmethod

from robot_hat.data_types.magnetometer import MagnetometerSample


class MagnetometerABC(ABC):
    """Vendor-neutral synchronous three-axis magnetometer interface."""

    @abstractmethod
    def initialize(self) -> None:
        """Validate and configure the physical sensor."""

    @abstractmethod
    def read_sample(self) -> MagnetometerSample:
        """Read one native-axis magnetic-field sample in teslas."""

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the implementation."""


__all__ = ["MagnetometerABC"]
