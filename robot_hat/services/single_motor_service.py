from typing import Optional, Sequence

from robot_hat.data_types.config.motor import MotorDirection
from robot_hat.data_types.motor import MotorServiceDirection, MotorZeroDirection
from robot_hat.interfaces.motor_abc import MotorABC
from robot_hat.services.base_motor_service import BaseMotorService

__all__ = ["SingleMotorService", "MotorServiceDirection", "MotorZeroDirection"]


class SingleMotorService(BaseMotorService):
    """
    Service for controlling one motor through the same movement API as MotorService.

    Example using a GPIO-driven DC motor:
    --------------
    ```python
    from robot_hat import GPIODCMotorConfig, MotorFactory, SingleMotorService

    motor = MotorFactory.create_motor(
        config=GPIODCMotorConfig(
            calibration_direction=1,
            name="lift_motor",
            max_speed=100,
            forward_pin=6,
            backward_pin=13,
            enable_pin=12,
            pwm=True,
        )
    )

    motor_service = SingleMotorService(motor=motor)

    # move forward
    motor_service.move(40, 1)

    # move backward
    motor_service.move(40, -1)

    # stop
    motor_service.stop_all()
    ```
    """

    def __init__(self, motor: MotorABC) -> None:
        """
        Initialize the SingleMotorService.
        """
        super().__init__()
        self.motor: Optional[MotorABC] = motor

    @property
    def motors(self) -> Sequence[MotorABC]:
        if self.motor is None:
            return ()
        return (self.motor,)

    @property
    def speed(self) -> float:
        """
        Get the absolute speed of the managed motor.
        """
        return abs(self.motor.speed if self.motor else 0)

    def update_calibration_speed(self, value: float, persist: bool = False) -> float:
        """
        Update the speed calibration offset for the managed motor.
        """
        assert self.motor, "Motor is None"
        return self.motor.update_calibration_speed(value, persist)

    def update_calibration_direction(
        self, value: MotorDirection, persist: bool = False
    ) -> MotorDirection:
        """
        Update the direction calibration for the managed motor.
        """
        assert self.motor, "Motor is None"
        return self.motor.update_calibration_direction(value, persist)

    def _set_motion(self, speed: float, direction: MotorServiceDirection) -> None:
        """
        Apply the movement command to the managed motor.
        """
        assert self.motor, "Motor is None"
        self.motor.set_speed(speed * direction)

    def _clear_motors(self) -> None:
        self.motor = None
