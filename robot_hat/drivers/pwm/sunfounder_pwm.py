"""
Sunfounder PWM Driver

This driver controls all channels on a Sunfounder PWM device via I2C.
"""

import logging
import math
from typing import Union

from robot_hat.data_types.bus import BusType
from robot_hat.exceptions import InvalidChannelNumber
from robot_hat.factories import register_pwm_driver
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC

_log = logging.getLogger(__name__)

NUM_TIMERS = 7


@register_pwm_driver
class SunfounderPWM(PWMDriverABC):
    DRIVER_TYPE = "Sunfounder"

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
        address: int,
        bus: BusType = 1,
        period: int = 4096,
        frame_width: int = 20000,
    ) -> None:
        """
        Initialize the SunfounderPWM device.


        Args:
            bus: I2C bus number or an SMBus instance.
            address: I2C address or list of addresses.
            period: The period (auto-reload register value) that determines the PWM resolution
            frame_width: The total frame width (in µs) that is used by a servo (for pulse width conversion).
        """
        self._frame_width = frame_width
        self._arr: int = period

        if address is None:
            super().__init__(address=self.ADDR, bus=bus)
        else:
            super().__init__(address=address, bus=bus)

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
        _log.debug(
            "Writing value %d (0x%02X): high=0x%02X, low=0x%02X to register 0x%02X",
            value,
            value,
            value_h,
            value_l,
            reg,
        )
        data = (value_l << 8) + value_h
        return self.bus.write_word_data(self.address, reg, data)

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

        _log.debug(
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

        Converts the pulse width in microseconds to timer ticks (0..ARR) based on the
        current frame width and ARR selected by set_pwm_freq(), then writes the value
        to the channel register.

        Channel-to-timer mapping:
          • Channels 0-15: timer = channel // 4
          • Channels 16-17: timer = 4
          • Channel 18:     timer = 5
          • Channel 19:     timer = 6

        Args:
            channel: The PWM channel number (0-19).
            pulse:   The pulse width in microseconds.
        """
        if not (0 <= channel <= 19):
            msg = f"Channel must be in range 0-19, got {channel}"
            _log.error(msg)
            raise InvalidChannelNumber(msg)

        if channel < 16:
            timer_index = channel // 4
        elif channel in (16, 17):
            timer_index = 4
        elif channel == 18:
            timer_index = 5
        else:
            timer_index = 6

        # Ensure frequency/ARR was configured
        if self._arr is None:
            raise RuntimeError(
                "set_pwm_freq() must be called before set_servo_pulse()."
            )

        ticks_float = (float(pulse) / float(self._frame_width)) * self._arr
        ticks = int(round(ticks_float))
        if ticks < 0:
            ticks = 0
        elif ticks > self._arr:
            ticks = self._arr

        reg = self.REG_CHN + channel
        _log.debug(
            "Setting servo pulse %d µs -> %d ticks (ARR=%d, frame=%d µs) on channel %d "
            "(using timer %d) to register 0x%02X",
            pulse,
            ticks,
            self._arr,
            self._frame_width,
            channel,
            timer_index,
            reg,
        )
        self._i2c_write(reg, ticks)

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
        _log.debug(
            "Setting duty cycle %.1f%% on channel %d (pulse=%d out of %d)",
            duty,
            channel,
            pulse_val,
            self._arr,
        )
        self._i2c_write(self.REG_CHN + channel, pulse_val)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )
    # Example usage: sweep servo on channel 0

    try:
        import time

        with SunfounderPWM(address=0x14, bus=1) as pwm:
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
        _log.info("Exiting on keyboard interrupt")
