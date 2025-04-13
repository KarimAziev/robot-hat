"""
HBridgeMotor is used when you want to control the motor using an external or
abstracted PWM driver (often over I²C).
"""

import logging
from typing import TYPE_CHECKING, Optional, Union

from robot_hat.drivers.pwm.sunfounder_pwm import PWMDriverABC
from robot_hat.exceptions import InvalidChannelName
from robot_hat.motor.config import MotorDirection
from robot_hat.motor.motor_abc import MotorABC
from robot_hat.motor.motor_calibration import MotorCalibration
from robot_hat.utils import constrain, validate_pwm_channel_name

if TYPE_CHECKING:
    from robot_hat import Pin

logger = logging.getLogger(__name__)


class HBridgeMotor(MotorCalibration, MotorABC):
    """
    This implementation provides a unified and abstracted motor control that relies on an external PWM driver.
    The motor is driven by a separate digital output pin for direction control and uses a PWM driver—adhering
    to the PWMDriverABC interface - to provide a variable speed control signal.

    Use Case:
      - Ideal for hardware setups where a dedicated PWM driver (e.g., PCA9685, SunfounderPWM) is used to control
        motor speed via I²C or another bus.
      - Both direction and speed are decoupled from low-level hardware details, enabling greater flexibility
        and resolution. The motor speed is controlled by a duty cycle, and the underlying driver sets the PWM
        frequency.
      - This approach is common for H-bridge motor implementations that leverage external PWM chips.

    Example wiring:
      - A digital output pin controls the motor's direction.
      - A PWM driver channel (provided via a PWMDriverABC implementation) is used to control motor speed.
      - No direct PWM initialization via GPIO is required; instead, the driver is configured with its bus address.
    """

    def __init__(
        self,
        dir_pin: "Pin",
        driver: "PWMDriverABC",
        channel: Union[int, str],
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        frequency: int = 50,
        name: Optional[str] = None,
    ):
        """
        Initialize the Motor with a direction pin and a unified PWM driver.

        Args:
            dir_pin: A digital output pin used to control the motor's direction.
              You must supply an object that has high() and low() methods.
            driver: A PWM driver instance (e.g. SunfounderPWM, PCA9685, etc.)
              that implements PWMDriverABC.
            channel: The channel number (e.g. 0–19) on the PWM driver to use.
            calibration_direction: Calibration factor for the motor direction (+1 or -1).
            calibration_speed_offset: Speed offset for calibration purposes.
            max_speed: Maximum speed value (interpreted as 100% duty cycle).
            frequency: PWM frequency in Hz (common value for motors is around 50 Hz, but use what fits your system).
            name: Optional name for the motor (used for logging).
        """
        super().__init__(
            calibration_direction=calibration_direction,
            calibration_speed_offset=calibration_speed_offset,
        )
        if isinstance(channel, str):
            if not validate_pwm_channel_name(channel):
                raise InvalidChannelName(
                    f"Invalid PWM channel's name {channel}. "
                    "The channel name must start with 'P' followed by one or more digits."
                )
            self.channel = int(channel[1:])

        else:
            self.channel = channel

        self.direction_pin = dir_pin
        self.driver = driver
        self.max_speed = max_speed
        self.name = name or f"Motor_channel_{channel}"
        self._speed: float = 0

        self.driver.set_pwm_freq(frequency)
        logger.debug(f"{self.name}: PWM frequency set to {frequency} Hz.")

    @property
    def speed(self) -> float:
        """Return the current motor speed in percentage."""
        return self._speed

    def _apply_speed_correction(self, speed: float) -> float:
        """
        Constrain the input speed between -max_speed and max_speed.

        Args:
            speed: The input speed percentage.

        Returns:
            The constrained speed value.
        """
        return constrain(speed, -self.max_speed, self.max_speed)

    def set_speed(self, speed: float) -> None:
        """
        Set the motor's movement speed and direction.

        A positive speed drives the motor forward and a negative speed reverses it.
        The given speed (percentage) is scaled to a duty cycle percentage.

        Args:
            speed: Desired speed percentage (range: -max_speed to +max_speed).
        """
        speed = self._apply_speed_correction(speed)

        duty = int((abs(speed) / self.max_speed) * 100)

        if speed >= 0:
            self.direction_pin.low()
            logger.debug(f"{self.name}: set direction to forward.")
        else:
            self.direction_pin.high()
            logger.debug(f"{self.name}: set direction to reverse.")

        self.driver.set_pwm_duty_cycle(self.channel, duty)
        logger.debug(f"{self.name}: speed set to {speed}% (duty cycle {duty}%).")
        self._speed = speed

    def stop(self) -> None:
        """
        Stop the motor by setting the PWM duty cycle to 0.
        """
        self.driver.set_pwm_duty_cycle(self.channel, 0)
        self._speed = 0
        logger.debug(f"{self.name}: motor stopped.")

    def close(self) -> None:
        """
        Clean up resources by closing both the PWM driver and the direction pin.
        """
        self.driver.close()
        self.direction_pin.close()
        logger.debug(f"{self.name}: resources closed.")

    def __repr__(self) -> str:
        return f"<Motor(name={self.name}, max_speed={self.max_speed}, current_speed={self._speed})>"
