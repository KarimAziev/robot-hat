"""
Sunfounder PWM Driver

This driver controls all channels on a Sunfounder PWM device via I2C.
"""

import logging
import math
import os
from typing import List, Optional, Union

from robot_hat.drivers.pwm.pwm_driver_abc import PWMDriverABC
from robot_hat.exceptions import InvalidChannelNumber
from robot_hat.i2c import I2C
from robot_hat.smbus_singleton import SMBus as SMBusSingleton

USE_MOCK = os.getenv("ROBOT_HAT_MOCK_SMBUS")
if USE_MOCK == "1":
    from robot_hat.mock.smbus2 import MockSMBus as SMBus  # type: ignore
else:
    from smbus2 import SMBus

logger = logging.getLogger(__name__)

NUM_TIMERS = 7


class SunfounderPWM(I2C, PWMDriverABC):
    REG_CHN = 0x20

    REG_PSC = 0x40
    REG_ARR = 0x44

    REG_PSC2 = 0x50
    REG_ARR2 = 0x54

    ADDR = [0x14, 0x15, 0x16]

    CLOCK = 72000000.0

    PRESCALER_SQRT_OFFSET = 5
    PRESCALER_SEARCH_WINDOW = 10

    def __init__(
        self,
        bus: Union[int, SMBus, SMBusSingleton] = 1,
        address: Optional[Union[int, List[int]]] = None,
        frame_width: int = 20000,
        *args,
        **kwargs,
    ):
        """
        Initialize the SunfounderPWM device.

        Note: Unlike the previous version that was bound to one channel (and its timer),
        this implementation controls ALL channels so that you can use arbitrary channels
        when calling set_servo_pulse(channel, pulse).

        Args:
            bus: I2C bus number or an SMBus instance.
            address: I2C address or list of addresses.
            frame_width: The total frame width (in µs) that is used by a servo (for pulse width conversion).
        """
        self._frame_width = frame_width
        self._arr: int = 4096

        if isinstance(bus, int):
            self._bus_num = bus
            self._bus = SMBus(bus)
            self._own_bus = True
            logger.debug("Created own SMBus on bus %d", bus)
        else:
            self._bus = bus
            self._own_bus = False
            logger.debug("Using injected SMBus instance")

        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)

        self._freq = 50
        self._prescaler = None

        self.set_pwm_freq(50)

    def _i2c_write(self, reg: int, value: int) -> None:
        """
        Write a 16-bit value to the specified I2C register.
        Splits the 16-bit value into two bytes and writes them.
        """
        value_h = value >> 8
        value_l = value & 0xFF
        logger.debug(
            "Writing value %d (0x%02X): high=0x%02X, low=0x%02X to register 0x%02X",
            value,
            value,
            value_h,
            value_l,
            reg,
        )
        self.write([reg, value_h, value_l])

    def set_pwm_freq(self, freq: Union[int, float]) -> None:
        """
        Set the PWM frequency for all timers.

        The method searches for an optimal prescaler and period (ARR) pair that approximates
        the desired frequency. Once determined, it writes the registers for all timers.

        Args:
            freq: Desired PWM frequency in Hertz.
        """
        self._freq = int(freq)
        result_ap = []
        accuracy_list = []

        st = max(
            1, int(math.sqrt(self.CLOCK / self._freq)) - self.PRESCALER_SQRT_OFFSET
        )

        for psc in range(st, st + self.PRESCALER_SEARCH_WINDOW):
            arr = int(self.CLOCK / self._freq / psc)
            result_ap.append((psc, arr))
            achieved = self.CLOCK / psc / arr
            accuracy_list.append(abs(self._freq - achieved))

        best_index = accuracy_list.index(min(accuracy_list))
        best_psc, best_arr = result_ap[best_index]

        self._prescaler = round(best_psc)
        self._arr = round(best_arr)

        logger.debug(
            "Setting PWM frequency to %d Hz: chosen prescaler=%d, period (ARR)=%d",
            self._freq,
            self._prescaler,
            self._arr,
        )

        for timer in range(NUM_TIMERS):
            if timer < 4:
                reg_psc = self.REG_PSC + timer
                reg_arr = self.REG_ARR + timer
            else:
                reg_psc = self.REG_PSC2 + (timer - 4)
                reg_arr = self.REG_ARR2 + (timer - 4)

            self._i2c_write(reg_psc, self._prescaler - 1)
            self._i2c_write(reg_arr, self._arr)

    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        """
        Set the pulse width (in microseconds) for a given channel.

        The channel-to-timer mapping is as follows:
          • Channels 0–15: timer = channel // 4
          • Channels 16–17: timer = 4
          • Channel 18:    timer = 5
          • Channel 19:    timer = 6

        The method writes the pulse width to the corresponding channel register.

        Args:
            channel: The PWM channel number (0–19).
            pulse: The pulse width in microseconds.
        """
        if not (0 <= channel <= 19):
            msg = f"Channel must be in range 0–19, got {channel}"
            logger.error(msg)
            raise InvalidChannelNumber(msg)

        timer_index: Optional[int] = None
        if channel < 16:
            timer_index = channel // 4
        elif channel in (16, 17):
            timer_index = 4
        elif channel == 18:
            timer_index = 5
        elif channel == 19:
            timer_index = 6

        reg = self.REG_CHN + channel
        logger.debug(
            "Setting pulse width %d µs on channel %d (using timer %d) to register 0x%02X",
            pulse,
            channel,
            timer_index,
            reg,
        )
        self._i2c_write(reg, pulse)

    def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
        """
        Set the PWM duty cycle for a specific channel.

        Args:
            channel: The PWM channel number (0–19).
            duty: The duty cycle as a percentage (0 - 100).

        The duty cycle is converted into a pulse value based on the period (ARR)
        computed by set_pwm_freq(), then written to the channel register.
        """
        if not (0 <= duty <= 100):
            raise ValueError(f"Duty cycle must be between 0 and 100, got {duty}.")

        assert self._arr is not None, "set_pwm_freq() must be called first"

        pulse_val = int((duty / 100.0) * self._arr)
        logger.debug(
            "Setting duty cycle %.1f%% on channel %d (pulse=%d out of %d)",
            duty,
            channel,
            pulse_val,
            self._arr,
        )
        self._i2c_write(self.REG_CHN + channel, pulse_val)

    def close(self) -> None:
        """
        Close the I2C bus if it was opened by this instance.
        """
        if self._own_bus:
            logger.debug("Closing SMBus on bus %d", self._bus_num)
            self._bus.close()

    def __enter__(self) -> "SunfounderPWM":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
