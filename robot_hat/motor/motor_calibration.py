import logging

from robot_hat.exceptions import MotorValidationError
from robot_hat.motor.config import MotorDirection

logger = logging.getLogger(__name__)


class MotorCalibration:
    def __init__(
        self,
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
    ):
        self.direction: MotorDirection = calibration_direction
        self.calibration_direction: MotorDirection = calibration_direction
        self.calibration_speed_offset = calibration_speed_offset
        self.speed_offset = calibration_speed_offset

    def update_calibration_speed(self, value: float, persist=False) -> float:
        """
        Update the temporary or permanent speed calibration offset for the motor.

        Args:
            value: New speed offset for calibration.
            persist: Whether the change should persist across resets.

        Returns:
            The updated speed offset.
        """
        self.speed_offset = value
        if persist:
            self.calibration_speed_offset = value
        return self.speed_offset

    def reset_calibration_speed(self) -> float:
        """
        Restore the speed calibration offset to its default state.

        Returns:
            The reset speed offset.
        """
        self.speed_offset = self.calibration_speed_offset
        return self.speed_offset

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
        if value not in (1, -1):
            raise MotorValidationError("Calibration value must be 1 or -1.")

        self.direction = value

        if persist:
            self.calibration_direction = value
        return self.direction

    def reset_calibration_direction(self) -> MotorDirection:
        """
        Restore the direction calibration to its default state.

        Returns:
            The reset direction calibration.
        """
        self.direction = self.calibration_direction
        return self.calibration_direction

    def reset_calibration(self) -> None:
        """
        Reset both the speed and direction calibrations to their default states.
        """
        self.reset_calibration_direction()
        self.reset_calibration_speed()
