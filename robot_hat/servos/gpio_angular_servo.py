"""
A wrapper for servos driven directly via Raspberry Pi GPIO (using gpiozero's AngularServo).
"""

import logging
from math import isfinite
from threading import RLock
from types import TracebackType
from typing import TYPE_CHECKING, Optional, Protocol, Type, Union, cast

from robot_hat.interfaces.servo_abc import ServoABC

if TYPE_CHECKING:
    from gpiozero import AngularServo

_log = logging.getLogger(__name__)


class _AngularServoFactory(Protocol):
    """gpiozero accepts None to acquire a servo pin without starting pulses."""

    def __call__(
        self,
        pin: Union[int, str],
        *,
        initial_angle: Optional[float],
        min_angle: float,
        max_angle: float,
        min_pulse_width: float,
        max_pulse_width: float,
    ) -> "AngularServo": ...


class GPIOAngularServo(ServoABC):
    """
    Servo wrapper for a device connected directly to a Raspberry Pi GPIO pin using gpiozero's AngularServo.

    This class provides a unified interface (ServoABC) for controlling a servo connected directly
    to a GPIO pin. The user must supply the pin number (or name) along with the minimum and maximum angles,
    and the corresponding pulse widths in microseconds.

    Example:
    ```python
    from robot_hat import GPIOAngularServo

    servo = GPIOAngularServo(
        pin=17, min_angle=-42, max_angle=44, min_pulse=1000, max_pulse=2000
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
        from gpiozero import AngularServo

        if not all(
            isfinite(value) for value in (min_angle, max_angle, min_pulse, max_pulse)
        ):
            raise ValueError("Servo angles and pulse widths must be finite")
        if min_angle >= max_angle:
            raise ValueError("min_angle must be less than max_angle")
        if not 0 < min_pulse < max_pulse:
            raise ValueError("Pulse widths must satisfy 0 < min_pulse < max_pulse")
        self.pin = pin
        self._lock = RLock()
        self._closed = False
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse

        # gpiozero's unannotated constructor infers float from its default,
        # although None is its documented detached initialization value.
        factory = cast(_AngularServoFactory, AngularServo)
        self._servo = factory(
            pin,
            initial_angle=None,
            min_angle=min_angle,
            max_angle=max_angle,
            min_pulse_width=min_pulse / 1e6,
            max_pulse_width=max_pulse / 1e6,
        )

        _log.debug(
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
        with self._lock:
            self._ensure_open()
            if not isfinite(angle):
                raise ValueError("Servo angle must be finite")
            clamped = max(self.min_angle, min(angle, self.max_angle))
            self._servo.angle = clamped
            _log.debug("Set servo on pin %s to angle %.2f°", self.pin, clamped)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Directly set the pulse width time in microseconds by converting it to an angle.

        The mapping is done linearly between (min_pulse, min_angle) and (max_pulse, max_angle).

        Args:
            pulse_width_time: The desired pulse width in microseconds.
        """
        with self._lock:
            self._ensure_open()
            if not isfinite(pulse_width_time):
                raise ValueError("Servo pulse width must be finite")
            pulse = max(self.min_pulse, min(pulse_width_time, self.max_pulse))
            angle = ((pulse - self.min_pulse) / (self.max_pulse - self.min_pulse)) * (
                self.max_angle - self.min_angle
            ) + self.min_angle
            self.angle(angle)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("GPIO servo is closed")

    def reset(self) -> None:
        """
        Reset the servo to its default (mid-point) position.
        """
        mid_angle = (self.min_angle + self.max_angle) / 2
        self.angle(mid_angle)
        _log.debug("Reset servo on pin %s to mid position %.2f°", self.pin, mid_angle)

    def close(self) -> None:
        """
        Release any resources used by the servo (i.e. free the GPIO pin).
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._servo.close()
            _log.debug("Closed GPIOAngularServo on pin %s", self.pin)

    def __enter__(self) -> "GPIOAngularServo":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            _log.error(
                f"An exception occurred during exiting exception type: {exc_type.__name__}"
            )
            if exc_value:
                _log.error(f"Exception value: {exc_value}")

            import traceback as tb

            if traceback:
                _log.error(f"Traceback: {''.join(tb.format_tb(traceback))}")
        self.close()


if __name__ == "__main__":
    from robot_hat.servos.gpio_angular_servo import GPIOAngularServo

    servo = GPIOAngularServo(
        pin=17, min_angle=-42, max_angle=44, min_pulse=1000, max_pulse=2000
    )
    servo.angle(15)
