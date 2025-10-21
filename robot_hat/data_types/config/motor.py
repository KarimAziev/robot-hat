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

    def __post_init__(self) -> None:
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
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
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
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
        }
    )
    backward_pin: Union[int, str] = field(
        metadata={
            "title": "Backward PIN",
            "description": (
                "The GPIO pin that the backward input of the motor driver chip is connected to."
            ),
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
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
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
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
            "description": "GPIO pin for the phase/direction control signal.",
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
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
                "The GPIO pin that the enable (speed) "
                "input of the motor driver chip is connected to."
            ),
            "examples": ["D4", "D5", "GPIO17", "BCM17", "BOARD11", "WPI0", 23, 24],
        },
    )


MotorConfigType = Union[I2CDCMotorConfig, GPIODCMotorConfig, PhaseMotorConfig]


if __name__ == "__main__":
    import argparse
    import dataclasses
    import json
    from typing import Any

    def parse_int_or_str(value: str) -> Any:
        """
        Try to parse a string as int (base 0 to allow hex like 0x40).
        If that fails, return the original string.
        """
        try:
            return int(value, 0)
        except Exception:
            return value

    parser = argparse.ArgumentParser(
        prog="motor_config_demo",
        description="Create and print a motor config (I2C/GPIO/Phase) for testing/demo.",
    )
    subparsers = parser.add_subparsers(dest="motor_type", required=True)

    # I2C DC Motor parser
    p_i2c = subparsers.add_parser(
        "i2c", help="I2C-driven DC motor (PWM driver + dir pin)"
    )
    p_i2c.add_argument("--name", default="left_motor", help="Human-readable motor name")
    p_i2c.add_argument("--calibration-direction", type=int, choices=[1, -1], default=1)
    p_i2c.add_argument("--max-speed", type=int, default=100)
    p_i2c.add_argument("--channel", default="P0", help="PWM channel (e.g. P0, 0)")
    p_i2c.add_argument("--dir-pin", default="D5", help="Direction pin (string or int)")

    # PWM driver options (I2C)
    p_i2c.add_argument("--driver-name", default="Sunfounder")
    p_i2c.add_argument("--driver-bus", type=int, default=1)
    p_i2c.add_argument("--driver-frame-width", type=int, default=20000)
    p_i2c.add_argument("--driver-freq", type=int, default=50)
    # allow hex address like 0x40
    p_i2c.add_argument("--driver-address", type=lambda s: int(s, 0), default=0x40)

    # GPIO DC Motor parser
    p_gpio = subparsers.add_parser("gpio", help="GPIO-driven DC motor (direct pins)")
    p_gpio.add_argument(
        "--name", default="right_motor", help="Human-readable motor name"
    )
    p_gpio.add_argument("--calibration-direction", type=int, choices=[1, -1], default=1)
    p_gpio.add_argument("--max-speed", type=int, default=90)
    p_gpio.add_argument(
        "--forward-pin",
        help="Forward GPIO pin (string or int)",
        default=20,
    )
    p_gpio.add_argument(
        "--backward-pin",
        help="Backward GPIO pin (string or int)",
        default=21,
    )
    p_gpio.add_argument(
        "--pwm",
        action="store_true",
        help="Use PWM output devices on the pins",
        default=True,
    )
    p_gpio.add_argument(
        "--enable-pin", help="Optional enable pin (string or int)", default=26
    )

    # Phase motor parser
    p_phase = subparsers.add_parser(
        "phase", help="Phase/enable motor driver configuration"
    )
    p_phase.add_argument("--name", required=True, help="Human-readable motor name")
    p_phase.add_argument(
        "--calibration-direction", type=int, choices=[1, -1], default=1
    )
    p_phase.add_argument("--max-speed", type=int, default=100)
    p_phase.add_argument("--phase-pin", required=True, help="Phase/direction GPIO pin")
    p_phase.add_argument("--pwm", action="store_true", help="Use PWM on enable pin")
    p_phase.add_argument("--enable-pin", required=True, help="Enable GPIO pin")

    args = parser.parse_args()

    # Construct the selected config
    if args.motor_type == "i2c":
        driver = PWMDriverConfig(
            name=args.driver_name,
            bus=args.driver_bus,
            frame_width=args.driver_frame_width,
            freq=args.driver_freq,
            address=args.driver_address,
        )

        channel = parse_int_or_str(args.channel)
        dir_pin = parse_int_or_str(args.dir_pin)

        cfg = I2CDCMotorConfig(
            calibration_direction=args.calibration_direction,
            name=args.name,
            max_speed=args.max_speed,
            driver=driver,
            channel=channel,
            dir_pin=dir_pin,
        )

    elif args.motor_type == "gpio":
        forward_pin = parse_int_or_str(args.forward_pin)
        backward_pin = parse_int_or_str(args.backward_pin)
        enable_pin = (
            parse_int_or_str(args.enable_pin) if args.enable_pin is not None else None
        )

        cfg = GPIODCMotorConfig(
            calibration_direction=args.calibration_direction,
            name=args.name,
            max_speed=args.max_speed,
            forward_pin=forward_pin,
            backward_pin=backward_pin,
            pwm=args.pwm,
            enable_pin=enable_pin,
        )

    elif args.motor_type == "phase":
        phase_pin = parse_int_or_str(args.phase_pin)
        enable_pin = parse_int_or_str(args.enable_pin)

        cfg = PhaseMotorConfig(
            calibration_direction=args.calibration_direction,
            name=args.name,
            max_speed=args.max_speed,
            phase_pin=phase_pin,
            pwm=args.pwm,
            enable_pin=enable_pin,
        )
    else:
        parser.error("Unknown motor type")

    # Print the dataclass and JSON representation for inspection
    print("Dataclass repr:")
    print(cfg)
    print("\nAs JSON:")
    print(json.dumps(dataclasses.asdict(cfg), indent=2))
