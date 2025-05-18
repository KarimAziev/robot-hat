from dataclasses import dataclass, field
from typing import Literal, Optional, Union

from robot_hat.data_types.config.pwm import PWMDriverConfig

MotorDirection = Literal[1, -1]


@dataclass
class MotorBaseConfig:
    calibration_direction: MotorDirection = field(
        metadata={
            "description": "Initial motor direction calibration (+1/-1)",
            "json_schema_extra": {"type": "motor_direction"},
            "examples": [1, -1],
            "ge": -1,
            "le": 1,
        }
    )
    name: str = field(
        metadata={
            "title": "Name",
            "description": "Human-readable name for the motor",
            "examples": ["left", "right"],
        }
    )
    max_speed: int = field(
        metadata={
            "title": "Max speed",
            "description": "Maximum allowable speed for the motor.",
            "examples": [100, 90],
            "gt": 0,
        }
    )

    def __post_init__(self):
        if self.calibration_direction not in [1, -1]:
            raise ValueError(
                f"`calibration_direction` for motor '{self.name}' must be either 1 or -1."
            )


@dataclass
class I2CDCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled via a PWM driver over I²C.
    """

    driver: PWMDriverConfig = field(
        metadata={
            "title": "PWM driver",
            "description": "The PWM driver chip configuration.",
        },
    )
    channel: Union[str, int] = field(
        metadata={
            "title": "PWM channel",
            "description": "PWM channel number or name.",
            "examples": ["P0", "P1", "P2", 0, 1, 2],
        },
    )
    dir_pin: Union[str, int] = field(
        metadata={
            "title": "Direction pin",
            "description": (
                "A digital output pin used to control the motor's direction."
            ),
            "examples": ["D4", "D5", 23, 24],
        }
    )


@dataclass
class GPIODCMotorConfig(MotorBaseConfig):
    """
    The configuration for the motor, which is controlled without I²C.

    Suitable when the motor driver board (eg. a Waveshare/MC33886-based module) does not require
    or use an external PWM driver and is controlled entirely through direct GPIO calls.
    """

    forward_pin: Union[int, str] = field(
        metadata={
            "title": "Forward PIN",
            "description": (
                "The GPIO pin that the forward input of the motor driver chip is connected to."
            ),
        }
    )
    backward_pin: Union[int, str] = field(
        metadata={
            "title": "Backward PIN",
            "description": (
                "The GPIO pin that the backward input of the motor driver chip is connected to."
            ),
        }
    )
    pwm: bool = field(
        metadata={
            "title": "PWM",
            "description": (
                "Whether to construct PWM Output Device instances for the motor controller pins, "
                "allowing both direction and speed control."
            ),
        },
    )
    enable_pin: Optional[Union[int, str, None]] = field(
        default=None,
        metadata={
            "title": "PWM (enable) pin",
            "description": (
                "The GPIO pin that enables the motor. "
                "Required for **some** motor controller boards."
            ),
        },
    )


@dataclass
class PhaseMotorConfig(MotorBaseConfig):
    """
    The configuration for the a phase/enable motor driver board.
    """

    phase_pin: Union[int, str] = field(
        metadata={
            "title": "Phase pin",
            "description": ("GPIO pin for the phase/direction control signal."),
        }
    )
    pwm: bool = field(
        metadata={
            "title": "PWM",
            "description": (
                "Whether to construct PWM Output Device instances for the motor controller pins, "
                "allowing both direction and speed control."
            ),
        },
    )

    enable_pin: Union[int, str] = field(
        metadata={
            "title": "PWM (enable) pin",
            "description": (
                "The GPIO pin that enables the motor. "
                "Required for **some** motor controller boards."
            ),
        },
    )


MotorConfig = Union[I2CDCMotorConfig, GPIODCMotorConfig, PhaseMotorConfig]


if __name__ == "__main__":

    pwm_config = PWMDriverConfig(
        name="Sunfounder", bus=1, frame_width=20000, freq=50, address=0x40
    )
    print("PWMDriverConfig address:", pwm_config.addr_str)

    i2c_dc_motor_config = I2CDCMotorConfig(
        calibration_direction=1,
        name="left_motor",
        max_speed=100,
        driver=pwm_config,
        channel="P0",
        dir_pin="D5",
    )
    print("I2CDCMotorConfig:", i2c_dc_motor_config)

    gpio_dc_motor_config = GPIODCMotorConfig(
        calibration_direction=-1,
        name="right_motor",
        max_speed=90,
        forward_pin=17,
        backward_pin=18,
        enable_pin=27,
        pwm=False,
    )
    print("GPIODCMotorConfig:", gpio_dc_motor_config)
