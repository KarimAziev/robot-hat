import logging
from typing import Optional, Union, cast

from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.motor.mixins.motor_calibration import MotorCalibration
from robot_hat.utils import constrain

_log = logging.getLogger(__name__)


class PhaseMotor(MotorCalibration, MotorABC):
    """
    A concrete motor implementation for a Phase/Enable motor driver board.

    This implementation uses gpiozero's PhaseEnableMotor class to handle a motor
    that has separate phase (direction) and enable (speed control) inputs.
    """

    def __init__(
        self,
        phase_pin: Union[int, str],
        enable_pin: Union[int, str],
        pwm: bool = True,
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        name: Optional[str] = None,
    ) -> None:
        """
        Initialize the motor with the specified GPIO pins.

        Args:
            phase_pin: GPIO pin for the phase/direction control signal.
            enable_pin: GPIO pin for the enable (PWM speed) control signal.
            pwm: Whether to use PWM output for speed control.
            calibration_direction: Calibration for the motor direction (+1 or -1).
            calibration_speed_offset: Adjustment for the motor speed calibration.
            max_speed: Maximum allowed speed (percentage value).
            name: Optional identifier for logging and debugging.
        """
        from gpiozero import PhaseEnableMotor

        super().__init__(
            calibration_direction=calibration_direction,
            calibration_speed_offset=calibration_speed_offset,
        )
        self._pwm = pwm
        self.max_speed = max_speed
        self.name = name or f"P{phase_pin}-E{enable_pin}"
        self._speed: float = 0

        self._motor = PhaseEnableMotor(phase=phase_pin, enable=enable_pin, pwm=pwm)
        _log.debug(
            f"Initialized PhaseMotor {self.name} with phase_pin={phase_pin}, enable_pin={enable_pin}"
        )

    @property
    def speed(self) -> float:
        """
        Return the current motor speed (percentage).
        """
        return self._speed

    def _apply_speed_correction(self, speed: float) -> float:
        """
        Apply calibration and constrain the speed value.

        Args:
            speed: The desired speed percentage.

        Returns:
            Adjusted speed after applying limits.
        """
        return constrain(speed, -self.max_speed, self.max_speed)

    def set_speed(self, speed: float) -> None:
        """
        Set the motor's speed and direction. Accepts values from
        -max_speed to +max_speed and converts them to the 0.0 to 1.0 PWM scale.

        A positive speed will run the motor forward (phase off) while a negative
        speed will run it backward (phase on). If PWM is disabled the motor will
        run at full speed in the desired direction.

        Args:
            speed: Target speed percentage within [-max_speed, max_speed].
        """
        speed = self._apply_speed_correction(speed)
        if speed > 0:
            if self._pwm:
                scale = speed / self.max_speed
                _log.debug(
                    f"{self.name}: Running forward at {speed}% (scale {scale:.2f})."
                )
                self._motor.forward(cast(int, scale))
            else:
                _log.debug(f"{self.name}: Running full forward (digital mode).")
                self._motor.forward(1)
        elif speed < 0:
            if self._pwm:
                scale = abs(speed) / self.max_speed
                _log.debug(
                    f"{self.name}: Running backward at {speed}% (scale {scale:.2f})."
                )
                self._motor.backward(cast(int, scale))
            else:
                _log.debug(f"{self.name}: Running full backward (digital mode).")
                self._motor.backward(1)
        else:
            self.stop()

        self._speed = speed

    def stop(self) -> None:
        """
        Stop the motor.
        """
        _log.debug(f"{self.name}: Motor stopped.")
        self._motor.stop()
        self._speed = 0

    def close(self) -> None:
        """
        Close the underlying GPIO resources.
        """
        try:
            self._motor.close()
        except Exception as e:
            _log.exception(f"Error closing motor resources: {e}")


def main() -> None:
    import argparse
    from time import sleep

    from robot_hat.utils import setup_env_vars

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    is_raspberry = setup_env_vars()
    default_enable_pin = 12 if is_raspberry else None

    parser = argparse.ArgumentParser(
        description="PhaseMotor test sequence using configurable GPIO pins."
    )
    parser.add_argument(
        "--phase-pin",
        type=int,
        default=5,
        help="GPIO pin for phase/direction control (default: 5)",
    )
    parser.add_argument(
        "--enable-pin",
        type=int,
        default=default_enable_pin,
        help="GPIO pin for enable (PWM) control (default: 12 on Raspberry Pi)",
    )
    parser.add_argument(
        "--pwm",
        action="store_true",
        help="Enable PWM mode for variable speed control.",
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

    motor = PhaseMotor(
        phase_pin=args.phase_pin,
        enable_pin=args.enable_pin,
        pwm=args.pwm,
        name="phase_motor",
    )

    _log.info("PhaseMotor test sequence starting. Press CTRL+C to exit.")
    try:
        while True:
            _log.info(f"Running forward at {args.forward_speed1}% speed.")
            motor.set_speed(args.forward_speed1)
            sleep(args.forward_duration)

            _log.info(f"Running forward at {args.forward_speed2}% speed.")
            motor.set_speed(args.forward_speed2)
            sleep(args.forward_duration)

            _log.info("Stopping motor.")
            motor.stop()
            sleep(args.pause)

            _log.info(f"Running backward at {abs(args.backward_speed)}% speed.")
            motor.set_speed(args.backward_speed)
            sleep(args.backward_duration)

            _log.info("Stopping motor.")
            motor.stop()
            sleep(args.pause)

    except KeyboardInterrupt:
        _log.info("Exiting and cleaning up resources...")

    finally:
        motor.stop()
        sleep(0.5)
        motor.close()


if __name__ == "__main__":
    main()
