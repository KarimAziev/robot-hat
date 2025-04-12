"""
PCA9685 16-Channel PWM Servo Driver

This module provides a class for controlling the PCA9685 over I2C.
"""

import logging
import math
import os
import time
from enum import IntEnum
from types import TracebackType
from typing import Optional, Type, Union

from robot_hat.drivers.pwm.pwm_driver_abc import PWMDriverABC
from robot_hat.smbus_singleton import SMBus as SMBusSingleton

logger = logging.getLogger(__name__)

USE_MOCK = os.getenv("ROBOT_HAT_MOCK_SMBUS")

if USE_MOCK == "1":
    from robot_hat.mock.smbus2 import MockSMBus as SMBus
else:
    from smbus2 import SMBus


class PCA9685Register(IntEnum):
    SUBADR1 = 0x02
    SUBADR2 = 0x03
    SUBADR3 = 0x04
    MODE1 = 0x00
    PRESCALE = 0xFE
    LED0_ON_L = 0x06
    LED0_ON_H = 0x07
    LED0_OFF_L = 0x08
    LED0_OFF_H = 0x09
    ALLLED_ON_L = 0xFA
    ALLLED_ON_H = 0xFB
    ALLLED_OFF_L = 0xFC
    ALLLED_OFF_H = 0xFD


class PCA9685(PWMDriverABC):
    """
    PCA9685 driver class, that enables to control the PCA9685 chip on the I2C bus.
    """

    def __init__(
        self,
        address: int,
        bus: Union[int, SMBus, SMBusSingleton] = 1,
        period: int = 4096,
        frame_width: Optional[int] = 20000,
    ) -> None:
        """
        Initialize the PCA9685.

        Args:

        `address`:  I2C address of the PCA9685.
        `bus`:      The I2C bus number (default is 1) or an already created instance of SMBus.
        `frame_width`: The length of time in microseconds (µs) between servo control pulses.
        `period`: The number of discrete steps per PWM cycle, determining the resolution of the PWM signal.
        """
        self._address: int = address
        self._period = period
        self._frame_width = frame_width if frame_width is not None else 20000
        if isinstance(bus, int):
            self._bus_num = bus
            self._bus = SMBus(bus)
            self._own_bus: bool = True
            logger.debug("Created own SMBus on bus %d", bus)
        else:
            self._bus = bus
            self._own_bus = False
            logger.debug("Using injected SMBus instance")
        logger.debug("Initializing PCA9685 at address 0x%02X", address)

        self._write(PCA9685Register.MODE1, 0x00)

    def _write(self, reg: int, value: int) -> None:
        """
        Write an 8-bit value to the specified register.

        Args:

        `reg`:    The register.
        `value`:  The 8-bit value to write.
        """
        try:
            self._bus.write_byte_data(self._address, int(reg), value)
            logger.debug("I2C: Write 0x%02X to register 0x%02X", value, int(reg))
        except Exception as e:
            logger.error("Failed to write to register 0x%02X: %s", int(reg), e)
            raise

    def _read(self, reg: PCA9685Register) -> int:
        """
        Read an unsigned byte from the specified register.

        Args:

        `reg`:  The register (from PCA9685Register enum).

        Returns:
                The value read.
        """
        try:
            result: int = self._bus.read_byte_data(self._address, int(reg))
            logger.debug(
                "I2C: Device 0x%02X returned 0x%02X from register 0x%02X",
                self._address,
                result & 0xFF,
                int(reg),
            )
            return result
        except Exception as e:
            logger.error("Failed to read from register 0x%02X: %s", int(reg), e)
            raise

    def set_pwm_freq(self, freq: int) -> None:
        """
        Set the PWM frequency.

        Args:

        `freq`:  The frequency in Hz.
        """
        # Calculate and set the prescaler.
        prescaleval: float = 25000000.0  # 25MHz oscillator
        prescaleval /= self._period  # 12-bit
        prescaleval /= float(freq)
        prescaleval -= 1.0
        logger.debug("Setting PWM frequency to %d Hz", freq)
        logger.debug("Estimated pre-scale: %f", prescaleval)

        prescale: int = int(math.floor(prescaleval + 0.5))
        logger.debug("Final pre-scale: %d", prescale)

        oldmode: int = self._read(PCA9685Register.MODE1)
        newmode: int = (oldmode & 0x7F) | 0x10  # sleep
        self._write(PCA9685Register.MODE1, newmode)  # go to sleep
        self._write(PCA9685Register.PRESCALE, prescale)
        self._write(PCA9685Register.MODE1, oldmode)
        time.sleep(0.005)
        self._write(PCA9685Register.MODE1, oldmode | 0x80)

    def set_pwm(self, channel: int, on: int, off: int) -> None:
        """
        Set a single PWM channel.

        Args:

        `channel`:  The channel number (0-15).
        `on`:       The count when the signal turns on.
        `off`:      The count when the signal turns off.
        """
        base_addr: int = int(PCA9685Register.LED0_ON_L) + 4 * channel
        self._write(base_addr, on & 0xFF)
        self._write(base_addr + 1, on >> 8)
        self._write(base_addr + 2, off & 0xFF)
        self._write(base_addr + 3, off >> 8)
        logger.debug("Channel: %d, LED_ON: %d, LED_OFF: %d", channel, on, off)

    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        """
        Set the servo pulse for a specific channel.

        `channel`  The channel number (0-15).
        `pulse`    The pulse length in microseconds.
        """
        # With a 50Hz PWM frequency, the period is 20000 µs.
        pulse_val: float = pulse * self._period / self._frame_width
        self.set_pwm(channel, 0, int(pulse_val))

    def close(self) -> None:
        """
        Close the I2C bus if it was created by this instance.
        """
        if self._own_bus:
            logger.debug("Closing SMBus on bus %d", self._bus_num)
            self._bus.close()

    def __enter__(self) -> "PCA9685":
        """
        Enable use as a context manager.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Ensure the bus is closed when exiting the context.
        """
        if exc_type is not None:
            logger.error("An exception occurred during PCA9685 __exit__")
            logger.error(f"Exception type: {exc_type.__name__}")
            if exc_value:
                logger.error(f"Exception value: {exc_value}")

            import traceback as tb

            if traceback:
                logger.error(f"Traceback: {''.join(tb.format_tb(traceback))}")
        self.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )
    # Example usage: sweep servo on channel 0
    try:
        with PCA9685(0x40, bus=1) as pwm:
            pwm.set_pwm_freq(50)
            while True:
                # Increase pulse width from 500µs to 2500µs.
                for pulse in range(500, 2500, 10):
                    pwm.set_servo_pulse(0, pulse)
                    time.sleep(0.02)
                # Decrease pulse width from 2500µs to 500µs.
                for pulse in range(2500, 500, -10):
                    pwm.set_servo_pulse(0, pulse)
                    time.sleep(0.02)
    except KeyboardInterrupt:
        logger.info("Exiting on keyboard interrupt")
