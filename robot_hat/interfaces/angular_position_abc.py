from abc import ABC, abstractmethod

from robot_hat.data_types.angular_position import (
    AngularPositionHealth,
    AngularPositionSample,
)


class AngularPositionABC(ABC):
    """Vendor-neutral interface for an absolute angular-position sensor."""

    @abstractmethod
    def initialize(self) -> None:
        """Validate and prepare the sensor for sampling."""
        pass

    @abstractmethod
    def read_angle(self) -> AngularPositionSample:
        """Return one timestamped absolute angular position."""
        pass

    @abstractmethod
    def read_health(self) -> AngularPositionHealth:
        """Return availability, sensor diagnostics, and error counters."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the sensor implementation."""
        pass


__all__ = ["AngularPositionABC"]
