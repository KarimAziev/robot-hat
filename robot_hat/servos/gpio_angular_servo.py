"""
A wrapper for servos driven directly via Raspberry Pi GPIO (using gpiozero's AngularServo).
"""

import logging
from typing import Union, cast

from gpiozero import AngularServo

from robot_hat.servos.servo_abc import ServoABC

logger = logging.getLogger(__name__)


class GPIOAngularServo(ServoABC):
    """
    Servo wrapper for a device connected directly to a Raspberry Pi GPIO pin using gpiozero's AngularServo.

    This class provides a unified interface (ServoABC) for controlling a servo connected directly
    to a GPIO pin. The user must supply the pin number (or name) along with the minimum and maximum angles,
    and the corresponding pulse widths in microseconds.

    Example:
    ```python
    from robot_hat.servos.gpio_angular_servo import GPIOAngularServo
    servo = GPIOAngularServo(
                pin=17,
                min_angle=-42,
                max_angle=44,
                min_pulse=1000,
                max_pulse=2000
            )
    servo.angle(15)
    ```
    """

    def __init__(
        self,
        pin: Union[int, str],
        min_angle: float = -90.0,
        max_angle: float = 90.0,
        min_pulse: int = 500,
        max_pulse: int = 2500,
    ) -> None:
        """
        Initialize the GPIOAngularServo.

        Args:
            pin: The GPIO pin number (or name) where the servo is connected.
            min_angle: The minimum angle the servo can rotate to.
            max_angle: The maximum angle the servo can rotate to.
            min_pulse: The pulse width (in microseconds) corresponding to min_angle.
            max_pulse: The pulse width (in microseconds) corresponding to max_angle.
        """
        self.pin = pin
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse

        self._servo = AngularServo(
            pin,
            min_angle=cast(int, min_angle),
            max_angle=cast(int, max_angle),
            min_pulse_width=min_pulse / 1e6,
            max_pulse_width=max_pulse / 1e6,
        )
        logger.debug(
            "Initialized GPIOAngularServo on pin %s with angle range (%.2f, %.2f)",
            pin,
            min_angle,
            max_angle,
        )

    def angle(self, angle: float) -> None:
        """
        Set the servo to the specified angle.

        Args:
            angle: The target angle in degrees.
        """
        clamped = max(self.min_angle, min(angle, self.max_angle))
        self._servo.angle = clamped
        logger.debug("Set servo on pin %s to angle %.2f°", self.pin, clamped)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Directly set the pulse width time in microseconds by converting it to an angle.

        The mapping is done linearly between (min_pulse, min_angle) and (max_pulse, max_angle).

        Args:
            pulse_width_time: The desired pulse width in microseconds.
        """
        pulse = max(self.min_pulse, min(pulse_width_time, self.max_pulse))
        angle = ((pulse - self.min_pulse) / (self.max_pulse - self.min_pulse)) * (
            self.max_angle - self.min_angle
        ) + self.min_angle
        self._servo.angle = angle
        logger.debug(
            "Translated pulse width %d µs on pin %s to angle %.2f°",
            pulse,
            self.pin,
            angle,
        )

    def reset(self) -> None:
        """
        Reset the servo to its default (mid-point) position.
        """
        mid_angle = (self.min_angle + self.max_angle) / 2
        self._servo.angle = mid_angle
        logger.debug("Reset servo on pin %s to mid position %.2f°", self.pin, mid_angle)

    def close(self) -> None:
        """
        Release any resources used by the servo (i.e. free the GPIO pin).
        """
        self._servo.close()
        logger.debug("Closed GPIOAngularServo on pin %s", self.pin)

    def __enter__(self) -> "GPIOAngularServo":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
