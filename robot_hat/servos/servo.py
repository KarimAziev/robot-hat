"""
Provides a Servo abstraction using an arbitrary PWM driver.

The driver must adhere to the PWMDriverABC interface.
"""

import logging
from typing import Union

from robot_hat.data_types.config.pwm import PWMDriverConfig
from robot_hat.exceptions import InvalidChannelName
from robot_hat.factories import PWMFactory
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC
from robot_hat.interfaces.servo_abc import ServoABC
from robot_hat.utils import parse_int_suffix

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
        """
        Initialize a Servo instance with the given PWM driver and configuration parameters.

        Parameters:
            `driver`:
                A PWM driver instance implementing the required interface to control pulse widths.
            `channel`:
                The identifier of the PWM channel to which the servo is
                connected. This can be an integer or a string ending with
                digits; if a string is provided, the trailing numeric part is
                used as the channel number, for example, P2 means channel 2.
            `min_angle`:
                The minimum logical angle (in degrees) that can be commanded to the servo.
            `max_angle`:
                The maximum logical angle (in degrees) that can be commanded to the servo.
            `min_pulse`:
                The minimum pulse width (in microseconds) corresponding to the servo's physical movement.
            `max_pulse`:
                The maximum pulse width (in microseconds) corresponding to the servo's physical movement.
            `real_min_angle`:
                The minimum physical angle (in degrees) that the servo can achieve. This value is used in
                the mapping from the logical angle to the physical angle.
            `real_max_angle`:
                The maximum physical angle (in degrees) that the servo can achieve. This value is used in
                the mapping from the logical angle to the physical angle.
        """

        if isinstance(channel, str):
            channel_int = parse_int_suffix(channel)
            if channel_int is None:
                raise InvalidChannelName(
                    f"Invalid PWM channel's name {channel}. "
                    "The channel name must end with one or more digits."
                )
            self.name = channel
            self.channel = channel_int

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


def main() -> None:
    import argparse
    import time

    def parse_args() -> argparse.Namespace:

        parser = argparse.ArgumentParser(
            description="Demo: Sweep a servo using a PCA9685 driver."
        )
        pwm_config_group = parser.add_argument_group(title="PWM config")
        servo_group = parser.add_argument_group(title="Servo")

        servo_group.add_argument(
            "--channel",
            type=int,
            default=0,
            help="PWM channel to which the servo is connected (default: 0).",
        )
        servo_group.add_argument(
            "--min-angle",
            type=int,
            default=-90,
            help="The minimum logical angle (in degrees) that can be commanded to the servo. (default -90)",
        )
        servo_group.add_argument(
            "--max-angle",
            type=int,
            default=90,
            help="The maximum logical angle (in degrees) that can be commanded to the servo.",
        )
        servo_group.add_argument(
            "--real-min-angle",
            type=int,
            default=-90,
            help="The minimum physical angle (in degrees) that the servo can achieve.",
        )
        servo_group.add_argument(
            "--real-max-angle",
            type=int,
            default=90,
            help="The maximum physical angle (in degrees) that the servo can achieve.",
        )
        servo_group.add_argument(
            "--min-pulse",
            type=int,
            default=500,
            help="The minimum pulse width (in microseconds) corresponding to the servo's physical movement.",
        )
        servo_group.add_argument(
            "--max-pulse",
            type=int,
            default=2500,
            help="The maximum logical angle (in degrees) that can be commanded to the servo.",
        )
        servo_group.add_argument(
            "--step",
            type=int,
            default=10,
            help="Angle step in degrees for each move (default: 10).",
        )
        servo_group.add_argument(
            "--delay",
            type=float,
            default=0.1,
            help="Delay in seconds between each movement (default: 0.1).",
        )

        pwm_config_group.add_argument(
            "--driver",
            default="PCA9685",
            choices=["PCA9685", "Sunfounder"],
            help="PWM driver to use.",
        )
        pwm_config_group.add_argument(
            "--address",
            type=lambda x: int(x, 0),
            default="0x40",
            help="I2C address of the PWM driver (default: 0x40). Prefix with '0x' for hex values.",
        )
        pwm_config_group.add_argument(
            "--bus", type=int, default=1, help="I2C bus number (default: 1)."
        )
        pwm_config_group.add_argument(
            "--freq",
            type=float,
            default=50,
            help="PWM frequency in Hz (default: 50). Typical for servos.",
        )
        pwm_config_group.add_argument(
            "--frame_width",
            type=int,
            default=20000,
            help="Frame Width in µs.",
        )

        return parser.parse_args()

    args = parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

    logging.info(
        "Driver: %s, I2C address: 0x%x, Bus: %d, Frequency: %0.1f Hz, Channel: %d",
        args.driver,
        args.address,
        args.bus,
        args.freq,
        args.channel,
    )

    pwm_config = PWMDriverConfig(
        address=args.address,
        name=args.driver,
        bus=args.bus,
        frame_width=args.frame_width,
        freq=args.freq,
    )

    logging.info("Starting servo sweep demo with the following parameters:")

    logging.info(
        "Angles: from %d° to %d° with a step of %d° and delay: %.2f s",
        args.min_angle,
        args.max_angle,
        args.step,
        args.delay,
    )

    try:

        with PWMFactory.create_pwm_driver(pwm_config) as pwm_driver:
            pwm_driver.set_pwm_freq(args.freq)

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
        logging.error("An error occurred: %s", e, exc_info=True)


if __name__ == "__main__":
    main()
