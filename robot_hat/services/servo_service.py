import logging
from enum import Enum
from typing import Callable, Optional, Union

from robot_hat.exceptions import InvalidCalibrationModeError
from robot_hat.servo import Servo
from robot_hat.utils import constrain

logger = logging.getLogger(__name__)


class ServoCalibrationMode(Enum):
    NEGATIVE = "negative"
    SUM = "sum"


class ServoService:
    """
    A high-level abstraction for managing servo operations, with support for
    flexibly applying calibration operations.

    Use this class to control a servo's angle with configurable constraints (min/max bounds),
    adjustable calibration offsets, and multiple calibration modes (built-in or custom). It is well-suited
    for servos requiring dynamic adjustments or fine-grained control.
    """

    def __init__(
        self,
        servo_pin: Union[str, int],
        min_angle=-90,
        max_angle=90,
        calibration_offset=0.0,
        name: Optional[str] = None,
        calibration_mode: Optional[
            Union[ServoCalibrationMode, Callable[[float, float], float]]
        ] = ServoCalibrationMode.SUM,
    ):
        """
        Initialize the ServoService with the specified configuration.

        Args:
        - servo_pin: The servo's pin name or number.
        - min_angle: Minimum allowable angle for the servo. Default is -90.
        - max_angle: Maximum allowable angle for the servo. Default is 90.
        - calibration_offset: A calibration offset for fine-tuning servo angles. Default is 0.0.
        - name: A name for the servo (useful for debugging/logging). Defaults to the servo pin if not provided.
        - calibration_mode: Specifies how calibration offsets are applied. Options include:
            - `ServoCalibrationMode.NEGATIVE`: Subtracts calibration, with adjustment multiplied by -1.
            - `ServoCalibrationMode.SUM`: Adds calibration directly to the input angle (default).
            - A custom calibration function: A callable function that takes `(angle, calibration_offset)`
              and returns a calibrated angle for more advanced customization.
            - `None`: Disables calibration entirely. Only the constrained angle value
              (within `min_angle` and `max_angle`) is passed directly to the hardware

        Raises:
        --------------
        - InvalidCalibrationModeError: If a provided `calibration_mode` is
          invalid (e.g., a non-callable that's not a `ServoCalibrationMode`).


        Example with `ServoCalibrationMode.SUM`, often suitable for steering servos (front wheels) in a robotics car.
        --------------
        ```python
        from robot_hat import ServoCalibrationMode, ServoService

        steering_servo = ServoService(
            servo_pin="P2",
            min_angle=-30,  # Maximum left turn
            max_angle=30,   # Maximum right turn
            calibration_mode=ServoCalibrationMode.SUM,  # Adds offset directly
            calibration_offset=-14.4,  # Adjust servo position for centered alignment
        )

        # Turn left
        steering_servo.set_angle(-30)

        # Turn slightly right
        steering_servo.set_angle(15)

        # Center position
        steering_servo.reset()
        # or
        steering_servo.reset()

        ```

        Example with `ServoCalibrationMode.NEGATIVE`, often suitable in the head servos.
        --------------
        ```python
        from robot_hat import ServoCalibrationMode, ServoService

        cam_tilt_servo = ServoService(
            servo_pin="P1",
            min_angle=-35,  # Maximum downward tilt
            max_angle=65,   # Maximum upward tilt
            calibration_mode=ServoCalibrationMode.NEGATIVE,  # Inverted adjustment
            calibration_offset=1.4,  # Adjust alignment for neutral center
        )

        # Tilt down
        cam_tilt_servo.set_angle(-20)

        # Tilt up
        cam_tilt_servo.set_angle(25)

        # Center position
        cam_tilt_servo.reset()
        ```

        """
        self.servo = Servo(servo_pin)
        self.min_angle = min_angle
        self.max_angle = max_angle
        self._persisted_calibration_offset = calibration_offset or 0.0
        self.calibration_offset = calibration_offset or 0.0
        self._current_angle = 0.0
        self.name = (
            name
            if name
            else servo_pin if isinstance(servo_pin, str) else f"{servo_pin}"
        )
        self._log_prefix = f"Servo {self.name or ''}".strip() + ": "

        self.calibration_function = (
            self._get_default_calibration_function(calibration_mode)
            if isinstance(calibration_mode, ServoCalibrationMode)
            else calibration_mode
        )
        self.servo.angle(self.calibration_offset)

    def _get_default_calibration_function(
        self, calibration_mode: ServoCalibrationMode
    ) -> Callable[[float, float], float]:
        """
        Return the default calibration function based on the specified mode.

        Args:
        - calibration_mode: The calibration mode to apply (`NEGATIVE` or `SUM`).

        Returns:
        - Callable[[float, float], float]: The appropriate calibration function.

        Raises:
        - InvalidCalibrationModeError: If the calibration mode is unsupported.
        """
        if calibration_mode == ServoCalibrationMode.SUM:
            return self.apply_sum_calibration
        elif calibration_mode == ServoCalibrationMode.NEGATIVE:
            return self.apply_negative_calibration
        raise InvalidCalibrationModeError(calibration_mode)

    @property
    def current_angle(self) -> float:
        """
        Get the current constrained angle of the servo (the value before applying calibration).

        Returns:
        - float: The current angle stored in the service.
        """
        return self._current_angle

    @current_angle.setter
    def current_angle(self, value: float):
        self._current_angle = value

    @staticmethod
    def apply_negative_calibration(value: float, calibration_value: float):
        """
        Apply a negative calibration adjustment to the given value.

        Formula:
            calibrated_value = -1 * (value + -1 * calibration_value)

        Args:
        - value (float): The input value to adjust.
        - calibration_value (float): The calibration offset to use.

        Returns:
        - float: The adjusted value.
        """
        return -1 * (value + -1 * calibration_value)

    @staticmethod
    def apply_sum_calibration(value: float, calibration_value: float):
        """
        Apply a sum calibration adjustment to the given value.

        Formula:
            calibrated_value = value + calibration_value

        Args:
        - value (float): The input value to adjust.
        - calibration_value (float): The calibration offset to use.

        Returns:
        - float: The adjusted value.
        """
        return value + calibration_value

    def set_angle(self, angle: float) -> None:
        """
        Set the servo's angle after applying constraints and calibration.

        1. Constrain the input `angle` to the `min_angle` and `max_angle` bounds.
        2. Apply calibration adjustments using the configured calibration function.
        3. Update and store the calibrated angle.

        Args:
        - angle (float): The desired input angle to set.

        Example Usage:
        >>> servo_service = ServoService("P1", min_angle=-45, max_angle=45, calibration_mode=ServoCalibrationMode.NEGATIVE)
        >>> servo_service.set_angle(30)
        """
        constrained_value = constrain(angle, self.min_angle, self.max_angle)
        calibrated_value = (
            self.calibration_function(angle, self.calibration_offset)
            if self.calibration_function is not None
            else constrained_value
        )

        logger.debug(
            self._log_prefix + "setting servo angle from %s to %s (calibrated: %s)",
            self.current_angle,
            angle,
            calibrated_value,
        )
        self.servo.angle(calibrated_value)
        self.current_angle = constrained_value

    def update_calibration(self, value: float, persist=False) -> float:
        """
        Update the temporary or permanent calibration offset for the servo.

        Args:
            value: The new offset.
            persist: Whether the change should persist across resets.

        Returns:
            The updated calibration offset.
        """
        logger.debug(
            (
                self._log_prefix + "updating and persisting"
                if persist
                else "updating" + "calibration offset from %s to %s"
            ),
            self.calibration_offset,
            value,
        )
        self.calibration_offset = value

        if persist:
            self._persisted_calibration_offset = value
        self.servo.angle(self.calibration_offset)
        return self.calibration_offset

    def reset_calibration(self) -> float:
        """
        Restore the direction calibration to its default state.

        Returns:
            The reset direction calibration.
        """
        logger.debug(
            "Resetting calibration offset from %s to %s",
            self.calibration_offset,
            self._persisted_calibration_offset,
        )
        self.calibration_offset = self._persisted_calibration_offset
        self.servo.angle(self.calibration_offset)
        return self.calibration_offset

    def reset(self) -> None:
        """
        Reset servo to its calibrated zero position.
        """
        self.set_angle(0)

    def __repr__(self):
        """
        Provide a string representation of the servo instance.

        Returns:
            A string showing key properties, like the servo name,
            maximum speed, and calibration details.
        """
        return (
            f"<Servo(name={self.name}, min_angle={self.min_angle}, max_angle={self.max_angle}"
            f"current_angle={self.current_angle}, "
            f"calibration_offset={self.calibration_offset}, _persisted_calibration_offset={self.calibration_offset})>"
        )
