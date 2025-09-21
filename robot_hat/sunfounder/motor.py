import logging
from typing import TYPE_CHECKING, Optional

from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.motor.mixins.motor_calibration import MotorCalibration
from robot_hat.utils import compose, constrain

if TYPE_CHECKING:
    from robot_hat import Pin
    from robot_hat.sunfounder.pwm import PWM

_log = logging.getLogger(__name__)


class Motor(MotorCalibration, MotorABC):
    """
    Represents a single motor with speed and direction control.
    """

    def __init__(
        self,
        dir_pin: "Pin",
        pwm_pin: "PWM",
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        period=4095,
        prescaler=10,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize the motor instance.

        Args:
            dir_pin: Pin instance used to control motor direction.
            pwm_pin: Pin instance used to control motor speed via PWM.
            calibration_direction: Initial calibration for the motor direction (+1 or -1).
            calibration_speed_offset: Adjustment for the motor speed calibration.
            max_speed: Maximum allowable speed percentage for the motor.
            period: PWM period value for speed control.
            prescaler: Prescaler value for PWM.
            name: Optional identifier for the motor for logging and debugging.
        """
        super().__init__(
            calibration_direction=calibration_direction,
            calibration_speed_offset=calibration_speed_offset,
        )
        self.name = name
        self.direction_pin = dir_pin
        self.speed_pin = pwm_pin
        self.period = period
        self.prescaler = prescaler
        self.max_speed = max_speed
        self._log_prefix = f"Motor {self.name or ''}".strip() + ": "
        self.speed_pin.period(self.period)
        self.speed_pin.prescaler(self.prescaler)

        self.speed_to_pwm_formula = compose(
            self._apply_pwm_constraints,
            self._apply_pwm_speed_correction,
            self._convert_speed_to_pwm,
        )
        self._speed: float = 0

    @property
    def speed(self) -> float:
        """Return the current motor speed in percentage."""
        return self._speed

    def _apply_speed_correction(self, speed: float) -> float:
        """
        Apply constrain to the speed to adjust for motor-specific variances.

        Args:
            speed: The desired speed percentage.

        Returns:
            Adjusted speed after calibration is applied.
        """
        return constrain(speed, -self.max_speed, self.max_speed)

    def _apply_pwm_speed_correction(self, speed: float) -> float:
        """
        Apply calibration to the speed to adjust for motor-specific variances.

        Args:
            speed: The desired speed percentage.

        Returns:
            Adjusted speed after calibration is applied.
        """
        return speed - self.speed_offset

    def _convert_speed_to_pwm(self, speed: float) -> float:
        """
        Convert a speed percentage to the corresponding PWM duty cycle.

        Args:
            speed: The speed percentage.

        Returns:
            The computed PWM value.
        """
        abs_speed = abs(speed)
        return int(abs_speed / 2) + 50 if abs_speed != 0 else 0

    def _apply_pwm_constraints(self, pwm: float) -> int:
        """
        Constrain a PWM value to ensure it remains within valid bounds (0-100).

        Args:
            pwm: The raw PWM value.

        Returns:
            Constrained PWM value within a valid range.
        """
        return int(constrain(pwm, 0, 100))

    def set_speed(self, speed: float) -> None:
        """
        Set the motor's speed and direction after applying calibration.

        A positive speed makes the motor move forward, and a negative speed
        makes it reverse. The speed is corrected and mapped to a PWM duty cycle.

        Args:
            speed: Target speed percentage within the range [-100, 100].
        """

        _log.debug(self._log_prefix + "setting speed %s", speed)
        speed = self._apply_speed_correction(speed)
        pwm_speed = self.speed_to_pwm_formula(speed)
        direction = self.direction if speed >= 0 else -self.direction

        if direction == -1:
            self.direction_pin.high()
        else:
            self.direction_pin.low()

        self.speed_pin.pulse_width_percent(int(pwm_speed))

        _log.debug(
            f"{self._log_prefix} set PWM speed {pwm_speed}, "
            f"direction: {'reverse' if direction == -1 else 'forward'}"
        )

        self._speed = speed

    def close(self) -> None:
        try:
            self.stop()
        except OSError as e:
            _log.error(f"{self._log_prefix}failed to stop motor: {e}")
        except Exception:
            _log.error("Failed to stop motors", exc_info=True)

        self.direction_pin.close()
        try:
            self.speed_pin.close()
        except OSError as e:
            _log.error(f"{self._log_prefix}failed to close speed pin: {e}")
        except Exception:
            _log.error("Failed to close speed pin", exc_info=True)

    def stop(self) -> None:
        """
        Stop the motor by setting the speed to zero.

        Ensures the PWM output is set to 0, bringing the motor to a halt.
        """
        self.speed_pin.pulse_width_percent(0)
        self._speed = 0
        _log.debug(self._log_prefix + "stopped")

    def __repr__(self) -> str:
        """
        Provide a string representation of the motor instance.

        Returns:
            A string showing key properties, like the motor name,
            maximum speed, and calibration details.
        """
        return (
            f"<Motor(name={self.name}, max_speed={self.max_speed}, "
            f"calibration_direction={self.calibration_direction}, "
            f"calibration_speed_offset={self.calibration_speed_offset})>"
        )
