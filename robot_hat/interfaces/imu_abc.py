from abc import ABC, abstractmethod

from robot_hat.data_types.imu import IMUSample


class IMUABC(ABC):
    """Vendor-neutral synchronous interface for a six-axis IMU."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize and configure the sensor. Raise an exception on failure."""
        pass

    @abstractmethod
    def read_sample(self) -> IMUSample:
        """Read one timestamped sample in m/s² and rad/s."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by the sensor implementation."""
        pass


# Compatibility import for applications written against robot-hat 2.5. The
# interface contract is intentionally the new SI-unit contract.
AbstractIMU = IMUABC


__all__ = ["AbstractIMU", "IMUABC"]
