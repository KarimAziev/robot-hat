from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.exceptions import MotorValidationError


class MotorCalibration:
    _direction: MotorDirection
    _calibration_direction: MotorDirection
    _calibration_speed_offset: float
    _speed_offset: float

    def __init__(
        self,
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
    ) -> None:
        self.direction = calibration_direction
        self.calibration_direction = calibration_direction
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

    def apply_calibration(self, speed: float, max_speed: float) -> tuple[float, float]:
        """Return the logical and electrically applied speed commands.

        ``speed`` is first constrained to the public logical range. Direction
        calibration then changes only the electrical polarity. The speed offset
        changes the magnitude of non-zero commands and can never start a stopped
        motor or reverse a command.

        Returns:
            A ``(logical_speed, applied_speed)`` pair. ``logical_speed`` is the
            constrained caller command exposed by motor ``speed`` properties;
            ``applied_speed`` includes direction and magnitude calibration.
        """
        if max_speed <= 0:
            raise MotorValidationError("Maximum motor speed must be greater than zero.")

        logical_speed = max(-max_speed, min(speed, max_speed))
        if logical_speed == 0:
            return 0.0, 0.0

        calibrated_magnitude = max(
            0.0,
            min(abs(logical_speed) + self.speed_offset, max_speed),
        )
        logical_sign = 1 if logical_speed > 0 else -1
        applied_speed = calibrated_magnitude * logical_sign * self.direction
        return logical_speed, applied_speed

    @property
    def direction(self) -> MotorDirection:
        """
        Return current motor direction.
        """
        return self._direction

    @direction.setter
    def direction(self, value: MotorDirection) -> None:
        if value not in (1, -1):
            raise MotorValidationError("Calibration value must be 1 or -1.")
        self._direction = value

    @property
    def calibration_direction(self) -> MotorDirection:
        """
        Return persisted motor direction.
        """
        return self._calibration_direction

    @calibration_direction.setter
    def calibration_direction(self, value: MotorDirection) -> None:
        if value not in (1, -1):
            raise MotorValidationError("Calibration value must be 1 or -1.")
        self._calibration_direction = value

    @property
    def calibration_speed_offset(self) -> float:
        return self._calibration_speed_offset

    @calibration_speed_offset.setter
    def calibration_speed_offset(self, value: float) -> None:
        self._calibration_speed_offset = value

    @property
    def speed_offset(self) -> float:
        return self._speed_offset

    @speed_offset.setter
    def speed_offset(self, value: float) -> None:
        self._speed_offset = value

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
