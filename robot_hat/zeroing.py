#!/usr/bin/env python3
import argparse
import time

from robot_hat import Servo
from robot_hat.drivers.pwm.pca9685 import PCA9685


def parse_args():
    parser = argparse.ArgumentParser(
        description="Control a servo connected via PCA9685."
    )
    parser.add_argument(
        "--channel", type=int, default=1, help="PWM channel for the servo (default: 1)"
    )
    parser.add_argument(
        "--address",
        type=lambda x: int(x, 0),
        default=0x40,
        help="I2C address of the PCA9685 device (default: 0x40). "
        "You can specify as hex (e.g. 0x40) or decimal.",
    )
    parser.add_argument(
        "--angle", type=int, default=0, help="Initial angle for the servo (default: 0)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    print(
        f"Setting servo at channel {args.channel}, address {hex(args.address)} to angle {args.angle}."
    )
    try:
        with PCA9685(address=args.address, bus=1) as pwm_driver:
            pwm_driver.set_pwm_freq(50)
            servo = Servo(driver=pwm_driver, channel=args.channel)
            while True:
                servo.angle(args.angle)
                print(f"Servo angle set to {args.angle} at channel {args.channel}")
                time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting.")
    except Exception as e:
        print("An error occurred:", e)
