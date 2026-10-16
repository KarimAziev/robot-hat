"""
This module is intended for cases where a motor is controlled directly via
GPIO pins without I²C.

gpiozero controls forward and reverse direction outputs, with optional PWM
on those outputs for speed control. A separate optional active-high enable
output gates the motor driver.

This class is suitable when the motor driver board (e.g., a
Waveshare/MC33886-based module) does not require or use an external PWM driver
and is controlled entirely through direct GPIO calls.
"""

import logging
from threading import RLock
from typing import Callable, Optional, Union, cast

from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.motor.mixins.motor_calibration import MotorCalibration
from robot_hat.utils import constrain

_log = logging.getLogger(__name__)


class GPIODCMotor(MotorCalibration, MotorABC):
    """
    This implementation controls a motor using direct GPIO control. It drives the motor by toggling
    GPIO output pins for forward and reverse directions.

    gpiozero PWMOutputDevice instances provide speed control on the direction
    pins when PWM is enabled.

    Use Case:
      - Ideal for hardware setups (like the Waveshare MC33886 module) that do not rely on a dedicated PWM
        driver.
      - The motor is controlled entirely via direct GPIO calls, and no I²C address or external PWM driver is needed.

    Example wiring:
      - Two GPIO pins are used for direction control (one for forward, one for reverse).
      - An optional third GPIO pin is a digital active-high enable, held low
        while the motor is stopped.
    """

    def __init__(
        self,
        forward_pin: Union[int, str],
        backward_pin: Union[int, str],
        pwm_pin: Union[int, str, None],
        pwm=True,
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize the motor with the specified GPIO pins.

        Args:
            forward_pin: GPIO pin for forward direction.
            backward_pin: GPIO pin for reverse direction.
            pwm_pin: Optional digital active-high enable pin for the motor driver.
            pwm: Whether to use PWM on the direction outputs for variable speed.
            calibration_direction: Initial calibration for the motor direction (+1 or -1).
            calibration_speed_offset: Adjustment for the motor speed calibration.
            name: Optional identifier for the motor for logging and debugging.
        """
        from gpiozero import DigitalOutputDevice, Motor

        self._lock = RLock()
        self._closed = False
        self._motor: Optional[Motor] = None
        self._enable: Optional[DigitalOutputDevice] = None

        super().__init__(
            calibration_direction=calibration_direction,
            calibration_speed_offset=calibration_speed_offset,
        )
        self._pwm = pwm
        self.max_speed = max_speed
        self.name = name or f"F{forward_pin}-B{backward_pin}-P{pwm_pin}"
        self._speed: float = 0
        self._applied_speed: float = 0
        try:
            # Hold the bridge disabled while its direction outputs are acquired.
            if pwm_pin is not None:
                self._enable = DigitalOutputDevice(pwm_pin, initial_value=False)
            self._motor = Motor(forward=forward_pin, backward=backward_pin, pwm=pwm)
        except Exception:
            self.close()
            raise
        _log.debug(
            f"Initialized motor {self.name} with forward_pin={forward_pin}, backward_pin={backward_pin}, pwm_pin={pwm_pin}"
        )

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def applied_speed(self) -> float:
        return self._applied_speed

    def _apply_speed_correction(self, speed: float) -> float:
        """
        Apply constrain to the speed to adjust for motor-specific variances.

        Args:
            speed: The desired speed percentage.

        Returns:
            Adjusted speed after calibration is applied.
        """
        return constrain(speed, -self.max_speed, self.max_speed)

    def set_speed(self, speed: float) -> None:
        """
        Set the motor's speed and direction.

        Accepts any speed in the interval [-max_speed, max_speed] and converts
        the value to a 0.0 to 1.0 range for gpiozero.

        If PWM is disabled, the motor is simply set to full forward (1), full backward (-1)
        or stopped (0).

        Args:
            speed: Target speed percentage within [-max_speed, max_speed].
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("Motor is closed")
            try:
                self._set_speed(speed)
            except Exception:
                try:
                    self.stop()
                except Exception:
                    _log.exception("Failed to stop motor after a command failure")
                raise

    def _set_speed(self, speed: float) -> None:
        assert self._motor is not None
        logical_speed, applied_speed = self.apply_calibration(speed, self.max_speed)
        if applied_speed == 0:
            self.stop()
            return

        applied_sign = 1 if applied_speed > 0 else -1

        if self._enable is not None:
            self._enable.off()

        if applied_sign > 0:
            command = self._motor.forward
            log_direction = "forward"
        else:
            command = self._motor.backward
            log_direction = "backward"

        if self._pwm:
            scale = abs(applied_speed) / self.max_speed
            _log.debug(
                "Motor set %s: logical=%s, applied=%s (scaled %.2f).",
                log_direction,
                logical_speed,
                applied_speed,
                scale,
            )
            command(cast(int, scale))
        else:
            _log.debug(f"Motor set full {log_direction} (digital).")
            command(1)
            applied_speed = applied_sign * self.max_speed

        if self._enable is not None:
            self._enable.on()

        self._speed = logical_speed
        self._applied_speed = applied_speed

    def stop(self) -> None:
        """
        Stop the motor.
        """
        with self._lock:
            if self._closed:
                return
            actions: list[Callable[[], None]] = []
            if self._enable is not None:
                actions.append(self._enable.off)
            if self._motor is not None:
                actions.append(self._motor.stop)
            first_error: Exception | None = None
            for action in actions:
                try:
                    action()
                except Exception as error:
                    if first_error is None:
                        first_error = error
            if first_error is not None and self._motor is not None:
                from gpiozero import OutputDevice

                # A composite stop can fail before reaching its second output.
                for output in (
                    self._motor.forward_device,
                    self._motor.backward_device,
                ):
                    try:
                        if isinstance(output, OutputDevice):
                            output.off()
                    except Exception:
                        _log.exception("Failed to clear motor direction output")
            if first_error is not None:
                raise first_error
            self._speed = 0
            self._applied_speed = 0
            _log.debug("Motor stopped.")

    def close(self) -> None:
        """
        Close the underlying resources.
        """
        with self._lock:
            if self._closed:
                return
            first_error: Exception | None = None
            actions: list[Callable[[], None]] = [self.stop]
            if self._motor is not None:
                actions.append(self._motor.close)
            if self._enable is not None:
                actions.append(self._enable.close)
            for action in actions:
                try:
                    action()
                except Exception as error:
                    if first_error is None:
                        first_error = error
                    _log.exception("Failed to stop or close motor output")
            self._closed = True
            if first_error is not None:
                raise first_error

    def __del__(self) -> None:
        """
        Destructor method.
        """
        try:
            self.close()
        except Exception:
            _log.exception("Failed to close motor during destruction")


def main() -> None:
    import argparse
    from time import sleep

    from robot_hat.utils import setup_env_vars

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    is_raspberry = setup_env_vars()
    default_left_pwm = 12 if is_raspberry else None
    right_default_pwm = 26 if is_raspberry else None

    parser = argparse.ArgumentParser(
        description="DCMotor test sequence using configurable GPIO pins and test parameters."
    )

    parser.add_argument(
        "--left-pwm",
        action="store_true",
        help="Enable PWM",
    )

    parser.add_argument(
        "--left-forward",
        type=int,
        default=6,
        help="GPIO pin for forward direction for left motor (default: 6)",
    )
    parser.add_argument(
        "--left-backward",
        type=int,
        default=13,
        help="GPIO pin for backward direction for left motor (default: 13)",
    )
    parser.add_argument(
        "--left-pwm-pin",
        type=int,
        default=default_left_pwm,
        help="GPIO PWM (enable) pin for left motor",
    )

    parser.add_argument(
        "--right-forward",
        type=int,
        default=20,
        help="GPIO pin for forward direction for right motor (default: 20)",
    )
    parser.add_argument(
        "--right-backward",
        type=int,
        default=21,
        help="GPIO pin for backward direction for right motor (default: 21)",
    )
    parser.add_argument(
        "--right-pwm",
        action="store_true",
        help="Enable PWM",
    )
    parser.add_argument(
        "--right-pwm-pin",
        type=int,
        default=right_default_pwm,
        help="GPIO PWM (enable) pin for right motor",
    )

    parser.add_argument(
        "--forward-speed1",
        type=float,
        default=50,
        help="Test speed (percentage) for initial forward run (default: 50)",
    )
    parser.add_argument(
        "--forward-speed2",
        type=float,
        default=100,
        help="Test speed (percentage) for maximum forward run (default: 100)",
    )
    parser.add_argument(
        "--backward-speed",
        type=float,
        default=-50,
        help="Test speed (percentage) for backward run (default: -50)",
    )
    parser.add_argument(
        "--forward-duration",
        type=float,
        default=3,
        help="Duration in seconds for forward runs (default: 3)",
    )
    parser.add_argument(
        "--backward-duration",
        type=float,
        default=3,
        help="Duration in seconds for backward runs (default: 3)",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=2,
        help="Pause duration in seconds between runs (default: 2)",
    )

    args = parser.parse_args()

    motorA = GPIODCMotor(
        forward_pin=args.left_forward,
        backward_pin=args.left_backward,
        pwm_pin=args.left_pwm_pin,
        pwm=args.left_pwm,
        name="left",
    )
    motorB = GPIODCMotor(
        forward_pin=args.right_forward,
        backward_pin=args.right_backward,
        pwm_pin=args.right_pwm_pin,
        pwm=args.right_pwm,
        name="right",
    )

    _log.info("Motor test sequence starting. Press CTRL+C to exit.")

    try:
        while True:
            _log.info(f"Motors running forward at {args.forward_speed1}% speed.")
            motorA.set_speed(args.forward_speed1)
            motorB.set_speed(args.forward_speed1)
            sleep(args.forward_duration)

            _log.info(f"Motors running forward at {args.forward_speed2}% speed.")
            motorA.set_speed(args.forward_speed2)
            motorB.set_speed(args.forward_speed2)
            sleep(args.forward_duration)

            _log.info("Stopping motors.")
            motorA.stop()
            motorB.stop()
            sleep(args.pause)

            _log.info(f"Motors running backward at {abs(args.backward_speed)}% speed.")
            motorA.set_speed(args.backward_speed)
            motorB.set_speed(args.backward_speed)
            sleep(args.backward_duration)

            _log.info("Stopping motors.")
            motorA.stop()
            motorB.stop()
            sleep(args.pause)

    except KeyboardInterrupt:
        _log.info("Exiting and cleaning up GPIO...")

    finally:
        motorA.stop()
        motorB.stop()
        sleep(0.5)
        motorA.close()
        motorB.close()


if __name__ == "__main__":
    main()
