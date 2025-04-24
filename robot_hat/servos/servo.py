"""
Provides a Servo abstraction using an arbitrary PWM driver.

The driver must adhere to the PWMDriverABC interface (such as the PCA9685).
"""

import logging
from typing import Union

from robot_hat.drivers.pwm.pwm_driver_abc import PWMDriverABC
from robot_hat.exceptions import InvalidChannelName
from robot_hat.servos.servo_abc import ServoABC
from robot_hat.utils import validate_pwm_channel_name

logger = logging.getLogger(__name__)


class Servo(ServoABC):
    """
    A servo motor abstraction using a PWM controller (.e.g., PCA9685).

    This class converts a target angle into a PWM pulse width (in microseconds) and commands the
    hardware driver (e.g., PCA9685) to output the corresponding signal on a specified channel.
    """

    def __init__(
        self,
        driver: PWMDriverABC,
        channel: Union[int, str],
        min_angle: float = -90.0,
        max_angle: float = 90.0,
        min_pulse: int = 500,
        max_pulse: int = 2500,
        real_min_angle: float = -90.0,
        real_max_angle: float = 90.0,
    ) -> None:

        if isinstance(channel, str):
            if not validate_pwm_channel_name(channel):
                raise InvalidChannelName(
                    f"Invalid PWM channel's name {channel}. "
                    "The channel name must start with 'P' followed by one or more digits."
                )
            self.name = channel
            self.channel = int(channel[1:])

        else:
            self.name = f"P{channel}"
            self.channel = channel

        self.driver = driver

        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_pulse = min_pulse
        self.max_pulse = max_pulse
        self.real_min_angle = real_min_angle
        self.real_max_angle = real_max_angle

    def angle(self, angle: float) -> None:
        """
        Set the servo to the specified angle.

        The angle is mapped to a pulse width in microseconds based on
        the configured min and max values.
        """
        logical_angle = max(self.min_angle, min(angle, self.max_angle))
        ratio = (logical_angle - self.min_angle) / (self.max_angle - self.min_angle)
        physical_angle = self.real_min_angle + ratio * (
            self.real_max_angle - self.real_min_angle
        )
        pulse_width = self.min_pulse + (
            (physical_angle - self.real_min_angle)
            / (self.real_max_angle - self.real_min_angle)
        ) * (self.max_pulse - self.min_pulse)
        pulse_width_int = int(round(pulse_width))
        logger.debug(
            "[%s]: Logical Angle=%s, mapped Physical Angle=%s, pulse_width=%s, pulse_width_int=%s, "
            "logical_range=(%s, %s), physical_range=(%s, %s)",
            self.name,
            logical_angle,
            physical_angle,
            pulse_width,
            pulse_width_int,
            self.min_angle,
            self.max_angle,
            self.real_min_angle,
            self.real_max_angle,
        )
        self.driver.set_servo_pulse(self.channel, pulse_width_int)

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Directly set the pulse width time in microseconds.

        This bypasses the angle-to-pulse conversion.

        Args:
            pulse_width_time: The desired pulse width in microseconds.
        """
        pulse = max(self.min_pulse, min(pulse_width_time, self.max_pulse))
        self.driver.set_servo_pulse(self.channel, int(round(pulse)))

    def reset(self) -> None:
        """
        Reset the servo to the zero (center) angle.
        """
        self.angle(0)

    def close(self) -> None:
        """
        If any resources need to be cleaned up, call the underlying driver's close method.
        """
        self.driver.close()

    def __repr__(self) -> str:
        """
        Return a string representation of the Servo.

        The representation includes the PWM channel, angle range, and pulse width range.

        Returns:
            A string that represents the Servo instance.
        """
        return (
            f"<Servo(channel={self.channel}, angle_range=({self.min_angle}, "
            f"{self.max_angle}), pulse_range=({self.min_pulse}, {self.max_pulse}))>"
        )


if __name__ == "__main__":
    import argparse
    import time

    def parse_args():
        parser = argparse.ArgumentParser(
            description="Demo: Sweep a servo using a PCA9685 driver."
        )

        parser.add_argument(
            "--driver",
            default="PCA9685",
            choices=["PCA9685", "Sunfounder"],
            help="PWM driver to use.",
        )
        parser.add_argument(
            "--address",
            type=lambda x: int(x, 0),
            default="0x40",
            help="I2C address of the PWM driver (default: 0x40). Prefix with '0x' for hex values.",
        )
        parser.add_argument(
            "--bus", type=int, default=1, help="I2C bus number (default: 1)."
        )
        parser.add_argument(
            "--frequency",
            type=float,
            default=50,
            help="PWM frequency in Hz (default: 50). Typical for servos.",
        )
        parser.add_argument(
            "--channel",
            type=int,
            default=0,
            help="PWM channel to which the servo is connected (default: 0).",
        )
        parser.add_argument(
            "--min_angle",
            type=int,
            default=-90,
            help="Minimum servo angle in degrees (default: -90).",
        )
        parser.add_argument(
            "--max_angle",
            type=int,
            default=90,
            help="Maximum servo angle in degrees (default: 90).",
        )
        parser.add_argument(
            "--step",
            type=int,
            default=10,
            help="Angle step in degrees for each move (default: 10).",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.1,
            help="Delay in seconds between each movement (default: 0.1).",
        )

        return parser.parse_args()

    args = parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

    from typing import Dict, Type

    from robot_hat.drivers.pwm.pca9685 import PCA9685
    from robot_hat.drivers.pwm.sunfounder_pwm import SunfounderPWM

    drivers: Dict[str, Union[Type[PCA9685], Type[SunfounderPWM]]] = {
        "PCA9685": PCA9685,
        "Sunfounder": SunfounderPWM,
    }

    driver_name: str = args.driver

    driver = drivers[driver_name]

    logging.info("Starting servo sweep demo with the following parameters:")
    logging.info(
        "Driver: %s, I2C address: 0x%x, Bus: %d, Frequency: %0.1f Hz, Channel: %d",
        driver_name,
        args.address,
        args.bus,
        args.frequency,
        args.channel,
    )
    logging.info(
        "Angles: from %d° to %d° with a step of %d° and delay: %.2f s",
        args.min_angle,
        args.max_angle,
        args.step,
        args.delay,
    )

    try:

        with driver(address=args.address, bus=args.bus) as pwm_driver:
            pwm_driver.set_pwm_freq(args.frequency)

            servo = Servo(driver=pwm_driver, channel=args.channel)
            while True:
                # Sweep from min_angle to max_angle
                for angle in range(args.min_angle, args.max_angle + 1, args.step):
                    servo.angle(angle)
                    logging.info("Servo angle set to %d°", angle)
                    time.sleep(args.delay)
                # Sweep back from max_angle to min_angle
                for angle in range(args.max_angle, args.min_angle - 1, -args.step):
                    servo.angle(angle)
                    logging.info("Servo angle set to %d°", angle)
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        logging.info("Exiting servo sweep demo.")
    except Exception as e:
        logging.error("An error occurred: %s", e)
