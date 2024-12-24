from typing import Optional, Union


class MotorConfig:
    """
    Configuration for initializing a motor.

    This class encapsulates all parameters needed to properly initialize
    and calibrate a motor instance and provides validation for them.
    """

    def __init__(
        self,
        dir_pin: Union[str, int],
        pwm_pin: Union[str, int],
        calibration_direction: int = 1,
        calibration_speed_offset: float = 0,
        max_speed: int = 100,
        period: int = 4095,
        prescaler: int = 10,
        name: Optional[str] = None,
    ):
        """
        Initialize the configuration.

        Args:
            dir_pin: Number of Pin controlling motor direction. Either the name as string, or number.
            pwm_pin: PWM channel number or name.
            calibration_direction: Initial motor direction calibration (+1/-1).
            calibration_speed_offset: Initial motor speed calibration offset.
            max_speed: Maximum allowable speed for the motor.
            period: PWM period for speed control.
            prescaler: PWM prescaler for speed control.
            name: human-readable name for the motor.
        """
        self.dir_pin = dir_pin
        self.pwm_pin = pwm_pin
        self.calibration_direction = calibration_direction
        self.calibration_speed_offset = calibration_speed_offset
        self.max_speed = max_speed
        self.period = period
        self.prescaler = prescaler
        self.name = name

        self._validate()

    def _validate(self):
        """
        Validate the configuration parameters.
        """
        if self.calibration_direction not in (-1, 1):
            raise ValueError(
                f"Invalid calibration_direction: {self.calibration_direction}. Must be 1 or -1."
            )
        if self.max_speed < 0:
            raise ValueError(
                f"Invalid max_speed {self.max_speed}. Must be non-negative."
            )

    def __repr__(self):
        """
        String representation of the configuration.
        """
        return (
            f"<MotorConfig(name={self.name}, dir_pin={self.dir_pin}, pwm_pin={self.pwm_pin}, "
            f"calibration_direction={self.calibration_direction}, "
            f"calibration_speed_offset={self.calibration_speed_offset}, max_speed={self.max_speed}, "
            f"period={self.period}, prescaler={self.prescaler})>"
        )
