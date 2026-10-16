import logging
from enum import Enum
from math import isfinite
from threading import RLock
from typing import Callable, Optional, Union

from robot_hat.exceptions import InvalidCalibrationModeError
from robot_hat.interfaces.servo_abc import ServoABC
from robot_hat.utils import constrain

_log = logging.getLogger(__name__)


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
        servo: ServoABC,
        name: str,
        min_angle: float = -90,
        max_angle: float = 90,
        calibration_offset: float = 0.0,
        reverse: bool = False,
        calibration_mode: Optional[
            Union[ServoCalibrationMode, Callable[[float, float], float]]
        ] = ServoCalibrationMode.SUM,
    ) -> None:
        """
        Initialize the ServoService with the specified configuration.

        Args:
        - servo: The servo intance.
        - min_angle: Minimum allowable angle for the servo. Default is -90.
        - max_angle: Maximum allowable angle for the servo. Default is 90.
        - calibration_offset: A calibration offset for fine-tuning servo angles. Default is 0.0.
        - name: A human readable name for the servo (useful for debugging/logging).
        - calibration_mode: Specifies how calibration offsets are applied. Options include:
            - `ServoCalibrationMode.NEGATIVE`: Subtracts calibration, with adjustment multiplied by -1.
            - `ServoCalibrationMode.SUM`: Adds calibration directly to the input angle (default).
            - A custom calibration function: A callable function that takes `(angle, calibration_offset)`
              and returns a calibrated angle for more advanced customization.
            - `None`: Disables calibration entirely. Only the constrained angle value
              (within `min_angle` and `max_angle`) is passed directly to the hardware

        - reverse: Indicates whether the input angle should be logically
                   reversed before being sent to the servo. When set to True, all input
                   angles passed to the set_angle method will be mirrored about the origin
                   (i.e., multiplied by -1) before applying constraints and calibration.
                   This is useful when the physical orientation of the servo requires
                   inversion of its direction to behave correctly (e.g., mirrored servo
                   mounting in a differential steering setup or mechanical linkage that
                   reverses motion).


        Raises:
        --------------
        - InvalidCalibrationModeError: If a provided `calibration_mode` is
          invalid (e.g., a non-callable that's not a `ServoCalibrationMode`).


        Example with `ServoCalibrationMode.SUM`, often suitable for steering servos (front wheels) in a robotics car.
        --------------
        ```python
        from robot_hat import ServoCalibrationMode, ServoService

        steering_servo = ServoService(
            name="steering",
            servo=my_servo_instance,
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
            name="tilt",
            servo=my_servo_instance,
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
        self._lock = RLock()
        self.servo: Optional[ServoABC] = None
        if not all(
            isfinite(value) for value in (min_angle, max_angle, calibration_offset)
        ):
            raise ValueError("Servo angles and calibration offset must be finite")
        if min_angle > max_angle:
            raise ValueError("min_angle must not exceed max_angle")
        if calibration_mode is not None and not (
            isinstance(calibration_mode, ServoCalibrationMode)
            or callable(calibration_mode)
        ):
            raise InvalidCalibrationModeError(calibration_mode)
        self.name = name
        self.min_angle = min_angle
        self.max_angle = max_angle
        self._persisted_calibration_offset = calibration_offset or 0.0
        self.calibration_offset = calibration_offset or 0.0
        self._current_angle = 0.0
        self._reverse = reverse
        self._log_prefix = f"Servo {self.name or ''}".strip() + ": "

        self.calibration_function = (
            self._get_default_calibration_function(calibration_mode)
            if isinstance(calibration_mode, ServoCalibrationMode)
            else calibration_mode
        )
        self.servo = servo
        try:
            self.set_angle(0)
        except Exception:
            try:
                self.close()
            except Exception:
                _log.exception("Failed to close servo after initialization failure")
            raise

    def _get_default_calibration_function(
        self, calibration_mode: ServoCalibrationMode
    ) -> Callable[[float, float], float]:
        """
        Return the default calibration function based on the specified mode.

        Args:
        - calibration_mode: The calibration mode to apply (`NEGATIVE` or `SUM`).

        Returns:
        - The appropriate calibration function.

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
        - The current angle stored in the service.
        """
        return self._current_angle

    @current_angle.setter
    def current_angle(self, value: float) -> None:
        self._current_angle = value

    @staticmethod
    def apply_negative_calibration(value: float, calibration_value: float) -> float:
        """
        Apply a negative calibration adjustment to the given value.

        Formula:
            calibrated_value = -1 * (value + -1 * calibration_value)

        Args:
        - value: The input value to adjust.
        - calibration_value: The calibration offset to use.

        Returns:
        - The adjusted value.
        """
        return -1 * (value + -1 * calibration_value)

    @staticmethod
    def apply_sum_calibration(value: float, calibration_value: float) -> float:
        """
        Apply a sum calibration adjustment to the given value.

        Formula:
            calibrated_value = value + calibration_value

        Args:
        - value (float): The input value to adjust.
        - calibration_value (float): The calibration offset to use.

        Returns:
        - The adjusted value.
        """
        return value + calibration_value

    def set_angle(self, angle: float) -> None:
        """
        Set the servo's angle after applying constraints and calibration.

        1. Constrain the input `angle` to the `min_angle` and `max_angle` bounds.
        2. Apply calibration adjustments using the configured calibration function.
        3. Update and store the calibrated angle.

        Args:
        The desired input angle to set.
        """
        with self._lock:
            self._write_angle(angle, self.calibration_offset)

    def _write_angle(self, angle: float, offset: float) -> None:
        if self.servo is None:
            raise RuntimeError("Servo service is closed")
        if not isfinite(angle) or not isfinite(offset):
            raise ValueError("Servo angle and calibration offset must be finite")
        constrained_value = constrain(
            angle if not self._reverse else -angle, self.min_angle, self.max_angle
        )
        calibrated_value = (
            self.calibration_function(constrained_value, offset)
            if self.calibration_function is not None
            else constrained_value
        )
        if not isfinite(calibrated_value):
            raise ValueError("Calibrated servo angle must be finite")

        _log.debug(
            self._log_prefix + "setting servo angle from %s to %s (calibrated: %s)",
            self.current_angle,
            angle,
            calibrated_value,
        )
        self.servo.angle(calibrated_value)
        self.current_angle = constrained_value

    def update_calibration(self, value: float, persist: bool = False) -> float:
        """
        Update the calibration offset and move to the calibrated zero position.

        Args:
            value: The new offset.
            persist: Whether the change should persist across resets.

        Returns:
            The updated calibration offset.
        """
        with self._lock:
            self._write_angle(0, value)
            self.calibration_offset = value
            if persist:
                self._persisted_calibration_offset = value
            return self.calibration_offset

    def reset_calibration(self) -> float:
        """
        Restore the direction calibration to its default state.

        Returns:
            The reset direction calibration.
        """
        with self._lock:
            return self.update_calibration(self._persisted_calibration_offset)

    def reset(self) -> None:
        """
        Reset servo to its calibrated zero position.
        """
        self.set_angle(0)

    def close(self) -> None:
        """
        Close servo.
        """
        with self._lock:
            servo, self.servo = self.servo, None
            if servo is not None:
                servo.close()

    def __del__(self) -> None:
        """
        Destructor method.
        """
        try:
            self.close()
        except Exception:
            _log.exception("Failed to close servo service")

    def __repr__(self) -> str:
        """
        Provide a string representation of the servo instance.

        Returns:
            A string showing key properties, like the servo name,
            maximum speed, and calibration details.
        """
        return (
            f"<Servo(name={self.name}, min_angle={self.min_angle}, max_angle={self.max_angle}, "
            f"current_angle={self.current_angle}, "
            f"calibration_offset={self.calibration_offset}, _persisted_calibration_offset={self.calibration_offset})>"
        )
