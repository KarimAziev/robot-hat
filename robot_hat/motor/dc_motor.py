import logging
from typing import Optional, cast

from gpiozero import Motor

from robot_hat.motor.config import MotorDirection
from robot_hat.motor.motor_abc import MotorABC
from robot_hat.motor.motor_calibration import MotorCalibration
from robot_hat.utils import constrain

logger = logging.getLogger(__name__)


class DCMotor(MotorCalibration, MotorABC):
    """
    A concrete motor implementation for the RPi Motor Driver board.
    """

    def __init__(
        self,
        forward_pin: int,
        backward_pin: int,
        pwm_pin: int,
        calibration_direction: MotorDirection = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        name: Optional[str] = None,
    ):
        """
        Initialize the motor with the specified GPIO pins.

        Args:
            forward_pin: GPIO pin for forward direction.
            backward_pin: GPIO pin for reverse direction.
            pwm_pin: PWM (enable) pin for speed control.
            calibration_direction: Initial calibration for the motor direction (+1 or -1).
            calibration_speed_offset: Adjustment for the motor speed calibration.
            name: Optional identifier for the motor for logging and debugging.
        """
        super().__init__(
            calibration_direction=calibration_direction,
            calibration_speed_offset=calibration_speed_offset,
        )
        self.max_speed = max_speed
        self.speed: float = 0
        self.name = name or f"F{forward_pin}-B{backward_pin}-P{pwm_pin}"
        self._motor = Motor(
            forward=forward_pin, backward=backward_pin, enable=pwm_pin, pwm=True
        )
        logger.debug(
            f"Initialized motor {self.name} with forward_pin={forward_pin}, backward_pin={backward_pin}, pwm_pin={pwm_pin}"
        )

    def _apply_speed_correction(self, speed: float) -> float:
        """
        Apply constrain to the speed to adjust for motor-specific variances.

        Args:
            speed: The desired speed percentage.

        Returns:
            Adjusted speed after calibration is applied.
        """
        return constrain(speed, -self.max_speed, self.max_speed)

    def set_speed(self, speed: float):
        """
        Set the motor's speed and direction. Accepts values in the interval [-100, 100].
        A positive value makes the motor rotate forward, a negative value in reverse,
        and 0 stops the motor.

        Args:
            speed: Target speed percentage within the range [-100, 100].
        """
        speed = self._apply_speed_correction(speed)
        if speed > 0:
            adj = speed / 100
            logger.debug(f"Motor set forward with speed {speed}% ({adj}).")
            self._motor.forward(cast(int, adj))
        elif speed < 0:
            adj = abs(speed) / 100
            logger.debug(f"Motor set backward with speed {speed}% ({adj}).")
            self._motor.backward(cast(int, adj))
        else:
            self.stop()

        self.speed = speed

    def stop(self):
        """
        Stop the motor.
        """
        logger.debug("Motor stopped.")
        self._motor.stop()
        self.speed = 0

    def close(self):
        """
        Close the underlying resources.
        """
        self._motor.close()


def main():
    import argparse
    from time import sleep

    parser = argparse.ArgumentParser(
        description="DCMotor test sequence using configurable GPIO pins and test parameters."
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
        "--left-pwm",
        type=int,
        default=12,
        help="GPIO PWM (enable) pin for left motor (default: 12)",
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
        type=int,
        default=26,
        help="GPIO PWM (enable) pin for right motor (default: 26)",
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

    motorA = DCMotor(
        forward_pin=args.left_forward,
        backward_pin=args.left_backward,
        pwm_pin=args.left_pwm,
        name="left",
    )
    motorB = DCMotor(
        forward_pin=args.right_forward,
        backward_pin=args.right_backward,
        pwm_pin=args.right_pwm,
        name="right",
    )

    print("Motor test sequence starting. Press CTRL+C to exit.")

    try:
        while True:
            print(f"Motors running forward at {args.forward_speed1}% speed.")
            motorA.set_speed(args.forward_speed1)
            motorB.set_speed(args.forward_speed1)
            sleep(args.forward_duration)

            print(f"Motors running forward at {args.forward_speed2}% speed.")
            motorA.set_speed(args.forward_speed2)
            motorB.set_speed(args.forward_speed2)
            sleep(args.forward_duration)

            print("Stopping motors.")
            motorA.stop()
            motorB.stop()
            sleep(args.pause)

            print(f"Motors running backward at {abs(args.backward_speed)}% speed.")
            motorA.set_speed(args.backward_speed)
            motorB.set_speed(args.backward_speed)
            sleep(args.backward_duration)

            print("Stopping motors.")
            motorA.stop()
            motorB.stop()
            sleep(args.pause)

    except KeyboardInterrupt:
        print("Exiting and cleaning up GPIO...")

    finally:
        motorA.stop()
        motorB.stop()
        sleep(0.5)
        motorA.close()
        motorB.close()


if __name__ == "__main__":
    main()
