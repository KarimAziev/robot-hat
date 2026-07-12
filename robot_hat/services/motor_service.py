from typing import Optional, Sequence

from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.data_types.motor import MotorServiceDirection, MotorZeroDirection
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.services.base_motor_service import BaseMotorService

__all__ = ["MotorService", "MotorServiceDirection", "MotorZeroDirection"]


class MotorService(BaseMotorService):
    """
    The service for managing a pair of motors (left and right).

    The MotorService provides methods for controlling both motors together,
    handling speed, direction, calibration, and steering.

    Attributes:
    - left_motor: Instance of the motor controlling the left side.
    - right_motor: Instance of the motor controlling the right side.


    Example using GPIO-driven DC motors:
    --------------
    ```python
    from robot_hat import GPIODCMotorConfig, MotorFactory, MotorService

    left_motor = MotorFactory.create_motor(
        config=GPIODCMotorConfig(
            calibration_direction=1,
            name="left_motor",
            max_speed=100,
            forward_pin=6,
            backward_pin=13,
            enable_pin=12,
            pwm=True,
        )
    )
    right_motor = MotorFactory.create_motor(
        config=GPIODCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            forward_pin=20,
            backward_pin=21,
            pwm=True,
            enable_pin=26,
        )
    )


    # move forward
    speed = 40
    motor_service = MotorService(left_motor=left_motor, right_motor=right_motor)

    motor_service.move(speed, 1)

    # increase speed
    motor_service.move(motor_service.speed + 10, 1)

    # move backward
    motor_service.move(speed, -1)

    # stop
    motor_service.stop_all()

    ```

    Example using I2C-driven DC motors:
    --------------
    ```python
    from robot_hat import (
        I2CDCMotorConfig,
        MotorFactory,
        MotorService,
        PWMDriverConfig,
        PWMFactory,
    )

    driver_cfg = PWMDriverConfig(
        name="Sunfounder", bus=1, frame_width=20000, freq=50, address=0x14
    )
    driver = PWMFactory.create_pwm_driver(driver_cfg, bus=1)

    motor_service = MotorService(
        left_motor=MotorFactory.create_motor(
            config=I2CDCMotorConfig(
                calibration_direction=1,
                name="left_motor",
                max_speed=100,
                driver=driver_cfg,
                channel="P12",
                dir_pin="D4",
            ),
            driver=driver,
        ),
        right_motor=MotorFactory.create_motor(
            config=I2CDCMotorConfig(
                calibration_direction=1,
                name="right_motor",
                max_speed=100,
                driver=driver_cfg,
                channel="P13",
                dir_pin="D5",
            ),
            driver=driver,
        ),
    )

    # Usage
    speed = 40
    motor_service.move(speed, 1)

    # increase speed
    motor_service.move(motor_service.speed + 10, 1)

    # move backward
    motor_service.move(speed, -1)

    # stop
    motor_service.stop_all()

    ```

    """

    def __init__(self, left_motor: "MotorABC", right_motor: "MotorABC") -> None:
        """
        Initialize the MotorService.
        """
        super().__init__()
        self.left_motor: Optional[MotorABC] = left_motor
        self.right_motor: Optional[MotorABC] = right_motor

    @property
    def motors(self) -> Sequence[MotorABC]:
        """
        Return the currently managed left and right motors.
        """
        return tuple(
            motor for motor in (self.left_motor, self.right_motor) if motor is not None
        )

    @property
    def speed(self) -> float:
        """
        Get the average speed of the motors.
        """

        return round(
            (
                abs(self.left_motor.speed if self.left_motor else 0)
                + abs(self.right_motor.speed if self.right_motor else 0)
            )
            / 2
        )

    def update_left_motor_calibration_speed(self, value: float, persist=False) -> float:
        """
        Update the speed calibration offset for the left motor.

        Args:
            value: New speed offset for calibration.
            persist: Whether to make the calibration persistent across resets.

        Returns:
            Updated speed calibration offset.

        Usage:
            >>> controller.update_left_motor_calibration_speed(5, persist=True)
        """
        assert self.left_motor, "Left motor is None"
        assert self.right_motor, "Right motor is None"
        return self.left_motor.update_calibration_speed(value, persist)

    def update_right_motor_calibration_speed(
        self, value: float, persist=False
    ) -> float:
        """
        Update the speed calibration offset for the right motor.

        Args:
            value: New speed offset for calibration.
            persist: Whether to make the calibration persistent across resets (default: False).

        Returns:
            float: Updated speed calibration offset.

        Usage:
            >>> controller.update_right_motor_calibration_speed(-3, persist=False)
        """
        assert self.left_motor, "Left motor is None"
        assert self.right_motor, "Right motor is None"
        return self.right_motor.update_calibration_speed(value, persist)

    def update_right_motor_calibration_direction(
        self, value: MotorDirection, persist=False
    ) -> MotorDirection:
        """
        Update the direction calibration for the right motor.

        Args:
            value: New calibration direction (+1 or -1).
            persist: Whether to make the calibration persistent across resets (default: False).

        Returns:
            int: Updated direction calibration.

        Usage:
            >>> controller.update_right_motor_calibration_direction(1, persist=False)
        """
        assert self.right_motor, "Right motor is None"
        return self.right_motor.update_calibration_direction(value, persist)

    def update_left_motor_calibration_direction(
        self, value: MotorDirection, persist=False
    ) -> MotorDirection:
        """
        Update the direction calibration for the left motor.

        Args:
            value: New calibration direction (+1 or -1).
            persist: Whether to make the calibration persistent across resets (default: False).

        Returns:
            int: Updated direction calibration.

        Usage:
            >>> controller.update_left_motor_calibration_direction(-1, persist=True)
        """
        assert self.left_motor, "Left motor is None"
        return self.left_motor.update_calibration_direction(value, persist)

    def _set_motion(self, speed: float, direction: MotorServiceDirection) -> None:
        """
        Apply the movement command to the left and right motors.
        """
        assert self.left_motor, "Left motor is None"
        assert self.right_motor, "Right motor is None"

        speed1 = speed * direction
        speed2 = -speed * direction

        self.left_motor.set_speed(speed1)
        self.right_motor.set_speed(speed2)

    def _clear_motors(self) -> None:
        self.right_motor = None
        self.left_motor = None

    def move_with_steering(
        self, speed: int, direction: MotorServiceDirection, current_angle=0
    ) -> None:
        """
        Move the robot with speed and direction, applying steering based on the current angle.

        Args:
            speed: Base speed for the robot (range: -100 to 100).
            direction: 1 for forward, -1 for backward.
            current_angle: Steering angle for turning (range: -100 to 100, default: 0).

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
        - speed: The base speed at which to move.
        - direction: 1 for forward, -1 for backward.
        - current_angle: Steering angle for turning (e.g., -100 to 100).
        """
        assert self.left_motor, "Left motor is None"
        assert self.right_motor, "Right motor is None"

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
