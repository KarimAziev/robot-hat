from typing import TYPE_CHECKING, Tuple

from robot_hat.pin import Pin
from robot_hat.pwm import PWM

from .motor import Motor

if TYPE_CHECKING:
    from .config import MotorConfig


class MotorFabric:
    """
    A factory class to create motor instances using `MotorConfig`.
    """

    @staticmethod
    def create_motor(config: "MotorConfig") -> Motor:
        """
        Create a motor instance from a MotorConfig.

        This method takes a `MotorConfig` object defining the initialization parameters
        for a motor (e.g., pins, calibration settings, and speed constraints) and returns
        a fully configured `Motor` instance.

        Args:
            config (MotorConfig): The motor configuration object (e.g., pin mappings, calibration).

        Returns:
            Motor: A new motor instance configured as per the MotorConfig.

        Example:
        --------------
        ```python
        from robot_hat.motor.motor_fabric import MotorFabric
        from robot_hat.motor.config import MotorConfig

        motor_config = MotorConfig(dir_pin="P1", pwm_pin="P3", name="LeftMotor")
        motor = MotorFabric.create_motor(motor_config)
        ```
        """
        return Motor(
            dir_pin=Pin(config.dir_pin),
            pwm_pin=PWM(config.pwm_pin),
            calibration_direction=config.calibration_direction,
            calibration_speed_offset=config.calibration_speed_offset,
            max_speed=config.max_speed,
            period=config.period,
            prescaler=config.prescaler,
            name=config.name,
        )

    @staticmethod
    def create_motor_pair(
        left_config: "MotorConfig", right_config: "MotorConfig"
    ) -> Tuple[Motor, Motor]:
        """
        Create a pair of motors (left and right) using their configurations.

        This method simplifies the creation of two corresponding motor instances (e.g., left and right),
        useful in differential drive systems or other scenarios requiring synchronized motor pairs.

        Args:
            left_config (MotorConfig): Configuration for the left motor.
            right_config (MotorConfig): Configuration for the right motor.

        Returns:
            Tuple[Motor, Motor]: A tuple containing the `left_motor` and `right_motor` instances.

        Example:
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
        ```
        """
        return (
            MotorFabric.create_motor(left_config),
            MotorFabric.create_motor(right_config),
        )
