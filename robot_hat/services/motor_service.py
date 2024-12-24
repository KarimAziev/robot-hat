import logging
import time
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from robot_hat.motor.motor import Motor


class MotorService:
    """
    The service for managing a pair of motors (left and right).

    The MotorService provides methods for controlling both motors together, handling speed, direction, calibration, and steering.

    Attributes:
    - left_motor (Motor): Instance of the motor controlling the left side.
    - right_motor (Motor): Instance of the motor controlling the right side.

    Simple exampe:
    --------------
    ```python
    from robot_hat import MotorConfig, MotorService, MotorFabric

    left_motor, right_motor = MotorFabric.create_motor_pair(
        MotorConfig(
            dir_pin="D4",
            pwm_pin="P12",
            name="LeftMotor",
        ),
        MotorConfig(
            dir_pin="D5",
            pwm_pin="P13",
            name="RightMotor",
        ),
    )
    motor_service = MotorService(left_motor=left_motor, right_motor=right_motor)

    # move forward
    speed = 40
    motor_service.move(speed, 1)

    # move backward
    motor_service.move(speed, -1)

    # stop
    motor_service.stop_all()
    ```
    """

    def __init__(self, left_motor: "Motor", right_motor: "Motor"):
        """
        Initialize the MotorService.
        """
        self.left_motor = left_motor
        self.right_motor = right_motor
        self.direction = 0

    def stop_all(self) -> None:
        """
        Stop both motors safely with a double-pulse mechanism.

        The motor speed control is set to 0% pulse width twice for each motor, with a small delay (2 ms) between the
        two executions. This ensures that even if a brief command or glitch occurs, the motors will come to a complete stop.

        Usage:
            >>> controller.stop_all()
        """
        logger.debug("Stopping motors")
        self._stop_all()
        time.sleep(0.002)
        self._stop_all()
        time.sleep(0.002)
        logger.debug("Motors Stopped")

    def move(self, speed: int, direction: int) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed (int): The base speed (-100 to 100).
        - direction (int): 1 for forward, -1 for backward.
        """
        speed1 = speed * direction
        speed2 = -speed * direction

        self.left_motor.set_speed(speed1)
        self.right_motor.set_speed(speed2)
        self.direction = direction

    @property
    def speed(self):
        """
        Get the average speed of the motors.
        """
        return round((abs(self.left_motor.speed) + abs(self.right_motor.speed)) / 2)

    def update_left_motor_calibration_speed(self, value: float, persist=False) -> float:
        """
        Update the speed calibration offset for the left motor.

        Args:
            value (float): New speed offset for calibration.
            persist (bool): Whether to make the calibration persistent across resets (default: False).

        Returns:
            float: Updated speed calibration offset.

        Usage:
            >>> controller.update_left_motor_calibration_speed(5, persist=True)
        """
        return self.left_motor.update_calibration_speed(value, persist)

    def update_right_motor_calibration_speed(
        self, value: float, persist=False
    ) -> float:
        """
        Update the speed calibration offset for the right motor.

        Args:
            value (float): New speed offset for calibration.
            persist (bool): Whether to make the calibration persistent across resets (default: False).

        Returns:
            float: Updated speed calibration offset.

        Usage:
            >>> controller.update_right_motor_calibration_speed(-3, persist=False)
        """
        return self.right_motor.update_calibration_speed(value, persist)

    def update_right_motor_calibration_direction(
        self, value: int, persist=False
    ) -> int:
        """
        Update the direction calibration for the left motor.

        Args:
            value (int): New calibration direction (+1 or -1).
            persist (bool): Whether to make the calibration persistent across resets (default: False).

        Returns:
            int: Updated direction calibration.

        Usage:
            >>> controller.update_left_motor_calibration_direction(-1, persist=True)
        """
        return self.right_motor.update_calibration_direction(value, persist)

    def update_left_motor_calibration_direction(self, value: int, persist=False) -> int:
        """
        Update the direction calibration for the right motor.

        Args:
            value (int): New calibration direction (+1 or -1).
            persist (bool): Whether to make the calibration persistent across resets (default: False).

        Returns:
            int: Updated direction calibration.

        Usage:
            >>> controller.update_right_motor_calibration_direction(1, persist=False)
        """
        return self.left_motor.update_calibration_direction(value, persist)

    def reset_calibration(self) -> None:
        """
        Resets the calibration for both the left and right motors, including speed and direction calibration.
        """
        for motor in [self.left_motor, self.right_motor]:
            motor.reset_calibration_direction()
            motor.reset_calibration_speed()

    def _stop_all(self):
        """
        Internal method to stop all motors.

        Stops both the left and right motors instantly without additional delays.
        """
        self.left_motor.stop()
        self.right_motor.stop()
        self.direction = 0

    def move_with_steering(self, speed: int, direction: int, current_angle=0) -> None:
        """
        Move the robot with speed and direction, applying steering based on the current angle.

        Args:
            speed (int): Base speed for the robot (range: -100 to 100).
            direction (int): 1 for forward, -1 for backward.
            current_angle (int, optional): Steering angle for turning (range: -100 to 100, default: 0).

            - A positive angle steers toward the right.
            - A negative angle steers toward the left.

        Logic:
        - The speed is adjusted for each motor based on the current angle to achieve the desired turn.

        Usage:
            1. Move forward:
                >>> controller.move(speed=80, direction=1)

            2. Move backward with a left turn:
                >>> controller.move(speed=50, direction=-1, current_angle=-30)

            3. Move forward with a right turn:
                >>> controller.move(speed=90, direction=1, current_angle=45)
        """
        """
        Move the robot forward or backward, optionally steering it based on the current angle.

        Args:
        - speed (int): The base speed at which to move.
        - direction (int): 1 for forward, -1 for backward.
        - current_angle (int): Steering angle for turning (e.g., -100 to 100).
        """

        speed1 = speed * direction
        speed2 = -speed * direction

        if current_angle != 0:
            abs_current_angle = abs(current_angle)
            power_scale = (100 - abs_current_angle) / 100.0
            if current_angle > 0:
                speed1 *= power_scale
            else:
                speed2 *= power_scale

        self.left_motor.set_speed(speed1)
        self.right_motor.set_speed(speed2)
        self.direction = direction
