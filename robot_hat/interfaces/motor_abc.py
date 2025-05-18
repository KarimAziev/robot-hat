import logging
from abc import ABC, abstractmethod

from robot_hat.data_types.config.motor import MotorDirection

logger = logging.getLogger(__name__)


class MotorABC(ABC):
    """
    Represents a single motor with speed and direction control.
    """

    @property
    @abstractmethod
    def direction(self) -> MotorDirection:
        pass

    @property
    @abstractmethod
    def calibration_direction(self) -> MotorDirection:
        pass

    @property
    @abstractmethod
    def calibration_speed_offset(self) -> float:
        pass

    @property
    @abstractmethod
    def speed_offset(self) -> float:
        pass

    @property
    @abstractmethod
    def speed(self) -> float:
        pass

    @abstractmethod
    def set_speed(self, speed: float) -> None:
        """
        Set the motor's speed and direction after applying calibration.

        A positive speed makes the motor move forward, and a negative speed
        makes it reverse.

        Args:
            speed: Target speed percentage within the range [-100, 100].
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the motor by setting the speed to zero.

        Ensures the PWM output is set to 0, bringing the motor to a halt.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the underlying resources.
        """
        pass

    @abstractmethod
    def update_calibration_speed(self, value: float, persist=False) -> float:
        """
        Update the temporary or permanent speed calibration offset for the motor.

        Args:
            value: New speed offset for calibration.
            persist: Whether the change should persist across resets.

        Returns:
            The updated speed offset.
        """
        pass

    @abstractmethod
    def reset_calibration_speed(self) -> float:
        """
        Restore the speed calibration offset to its default state.

        Returns:
            The reset speed offset.
        """
        pass

    @abstractmethod
    def update_calibration_direction(
        self, value: MotorDirection, persist=False
    ) -> MotorDirection:
        """
        Update the temporary or permanent direction calibration for the motor.

        Args:
            value: New calibration direction (+1 or -1).
            persist: Whether the change should persist across resets.

        Returns:
            The updated direction calibration.
        """
        pass

    @abstractmethod
    def reset_calibration_direction(self) -> MotorDirection:
        """
        Restore the direction calibration to its default state.

        Returns:
            The reset direction calibration.
        """
        pass

    @abstractmethod
    def reset_calibration(self) -> None:
        """
        Reset both the speed and direction calibrations to their default states.
        """
        pass
