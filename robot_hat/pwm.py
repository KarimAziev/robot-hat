"""
A module to manage Pulse Width Modulation (PWM) to control the power delivered to devices like LEDs, motors, etc.
"""

import logging
import math
from typing import Dict, List, Optional, Union

from robot_hat.exceptions import InvalidChannelName, InvalidChannelNumber
from robot_hat.i2c import I2C
from robot_hat.pin_descriptions import pin_descriptions

logger = logging.getLogger(__name__)

timer: List[Dict[str, int]] = [{"arr": 1}] * 7

PRESCALER_SQRT_OFFSET = (
    5  # The offset applied to the square root result in prescaler calculation.
)
PRESCALER_SEARCH_WINDOW = 10  # The window size of prescaler values to search for the optimal prescaler-period pair.


class PWM(I2C):
    """
    This class provides an interface to generate and manage Pulse Width Modulation (PWM) signals.

    Key Concepts
    --------------
    - High Pulse: The duration when the signal is in a high state (logic 1).
    - Low Pulse:  The duration when the signal is in a low state (logic 0).
    - Period (T): The total time of one complete cycle, which includes both the high and low pulses.
    - Duty Cycle: The fraction of time a signal stays high during a period.
      Higher duty cycles deliver more power.

    PWM Waveform Representation
    --------------

    ```
    ^
    |          ____       ____       ____
    |         |    |     |    |     |    |
    |         |    |     |    |     |    |
    | ____    |    |_____|    |_____|    |_____ Time →
    |<---T--->|<---T--->|<---T--->|<---T--->
    ```

    1. Vertical Axis (signal state): Represents the state of the signal:
       - High (logic 1) – when the waveform is at its upper level (e.g., `5V` for a digital signal).
       - Low (logic 0) – when the waveform is at its lower level (e.g., `0V`).

    2. Horizontal Axis (time): Represents the progression of time. The cycles
       repeat periodically, with each cycle having a duration of time `T` (the
       period).

    3. Period (T): The horizontal distance (or time) between the start of one
       pulse and the start of the next.

    Example:

    ```python
    import time

    speed = 70 # desired motor speed from 0 to 100
    motor_speed_pwm = PWM("P12")
    period = 4095
    prescaler = 10
    max_speed = 100
    pwm_speed = max(0, min(max_speed, int(speed / 2) + 50)) # 85
    motor_speed_pwm.pulse_width_percent(pwm_speed)
    time.sleep(2) # move two seconds
    motor_speed_pwm.pulse_width_percent(0) # stop
    ```

    """

    REG_CHN = 0x20
    """Channel register prefix"""
    REG_PSC = 0x40
    """Prescaler register prefix"""
    REG_ARR = 0x44
    """Period register prefix"""

    REG_PSC2 = 0x50
    """Prescaler register prefix"""

    REG_ARR2 = 0x54
    """Period registor prefix"""

    ADDR = [0x14, 0x15, 0x16]
    """List of I2C addresses that the PWM controller can use."""

    CLOCK = 72000000.0
    """Clock frequency for in Hertz"""

    def __init__(
        self,
        channel: Union[int, str],
        address: Optional[Union[int, List[int]]] = None,
        *args,
        **kwargs,
    ):
        """
        Initialize the PWM module.

        Args:
            channel (int or str): PWM channel number (0-19/P0-P19).
            address (Optional[List[int]]): I2C device address or list of addresses.
        """
        if address is None:
            super().__init__(self.ADDR, *args, **kwargs)
        else:
            super().__init__(address, *args, **kwargs)

        self._chan_desc = pin_descriptions.get(
            (
                channel
                if isinstance(channel, str)
                else f"P{channel}" if isinstance(channel, int) else "unknown"
            ),
            "unknown",
        )

        if isinstance(channel, str):
            if channel.startswith("P"):
                channel = int(channel[1:])
            else:
                msg = f'PWM channel should be between [P0, P19], not "{channel}"'
                logger.error(msg)
                raise InvalidChannelName(msg)
        if isinstance(channel, int):
            if channel > 19 or channel < 0:
                msg = f'channel must be in range of 0-19, not "{channel}"'
                raise InvalidChannelNumber(msg)

        if isinstance(self.address, int):
            logger.debug(
                "Initted PWM at the address %s",
                hex(self.address),
            )
        else:
            logger.warning(
                "PWM address %s is not found for channel %s (%s)",
                address,
                channel,
                self._chan_desc,
            )

        self.channel = channel
        if channel < 16:
            self.timer = int(channel / 4)
        elif channel == 16 or channel == 17:
            self.timer = 4
        elif channel == 18:
            self.timer = 5
        elif channel == 19:
            self.timer = 6
        self._pulse_width = 0
        self._freq = 50
        self.freq(50)

    def _i2c_write(self, reg: int, value: int) -> None:
        """
        Write a 16-bit value to a specified I2C register.

        This method writes to a device over the I2C bus. It takes a 16-bit value, splits it into
        a high byte (most significant byte) and a low byte (least significant byte), and writes
        these two bytes sequentially to the given 8-bit register.

        The operation is typically used to configure or send data to devices such as sensors,
        memory chips, or display controllers via an I2C interface.

        Args:
            reg (int): An 8-bit register address on the I2C device where the data will be written.
            value (int): A 16-bit integer value that will be split into two 8-bit bytes. The
                         most significant byte (high byte) will be sent first, followed by the
                         least significant byte (low byte).

        I2C Write Format:
            The data sent via the `write` method is structured as:
            [register address, high byte, low byte]

            - The high byte is extracted by shifting the 16-bit value 8 bits to the right.
            - The low byte is extracted using a bitwise AND with 0xFF to mask the upper bits.

        Example:
            If `reg = 0x05` and `value = 0x1234`:
                - High byte (`value_h`) = 0x12
                - Low byte (`value_l`) = 0x34
            The data written would be [0x05, 0x12, 0x34].

        Returns:
            None
        """
        value_h = (
            value >> 8
        )  # High byte: Shift right 8 bits to extract the most significant byte
        value_l = (
            value & 0xFF
        )  # Low byte: Mask with 0xFF to keep only the least significant byte
        # Write the register address followed by the high and low bytes to the I2C device

        logger.debug(
            "[%s]: writing 16 bit %s (%s) high byte: %s (%s) low byte: %s, (%s)",
            self._chan_desc,
            value,
            hex(value),
            value_h,
            hex(value_h),
            value_l,
            hex(value_l),
        )
        self.write([reg, value_h, value_l])

    def get_freq(self) -> float:
        "Get the current PWM frequency in Hertz."
        return self._freq

    def freq(self, freq: Union[float, int]) -> None:
        """
        Set the PWM frequency in Hertz.

        Note: The frequency should be in the range of 0 to 65535 Hz, but realistic values are usually lower.

        Args:
            freq: Desired PWM frequency in Hertz.

        Example:
            ```python
            pwm_controller.freq(1000)  # Set PWM frequency to 1 kHz
            ```

        Method Details:
            1. It calculates several prescaler and period values based on the provided frequency.
            2. For each combination, it checks how close the actual frequency (derived from prescaler and period)
               is to the desired frequency.
            3. It selects the best prescaler and period values that produce the closest result, and updates hardware registers.
        """
        self._freq = int(freq)

        result_ap: List[List[int]] = []
        acurracy_list: List[float] = []

        # Estimate prescaler values and adjust for accuracy
        st = max(1, int(math.sqrt(self.CLOCK / self._freq)) - PRESCALER_SQRT_OFFSET)

        for psc in range(st, st + PRESCALER_SEARCH_WINDOW):
            arr = int(self.CLOCK / self._freq / psc)
            result_ap.append([psc, arr])
            acurracy_list.append(abs(self._freq - self.CLOCK / psc / arr))

        i = acurracy_list.index(min(acurracy_list))

        psc, arr = result_ap[i]

        logger.debug(
            "[{%s}]: frequency {%s} -> prescaler {%s}, period: {%s}",
            self._chan_desc,
            self._freq,
            psc,
            arr,
        )

        self.prescaler(psc)
        self.period(arr)

    def get_prescaler(self) -> int:
        "Get the PWM prescaler value."
        return self._prescaler

    def prescaler(self, prescaler: Union[float, int]) -> None:
        """
        Set the PWM prescaler value.

        The prescaler divides the clock input, which directly affects the speed of the PWM cycle.

        A larger prescaler value means the PWM cycles more slowly.

        Args:
            prescaler: The prescaler value to set. It should be between 0 and 65535.

        ## Example:
        ```python
        pwm_controller.prescaler(1200)  # Set prescaler to 1200
        ```
        """
        self._prescaler = round(prescaler)
        self._freq = self.CLOCK / self._prescaler / timer[self.timer]["arr"]
        if self.timer < 4:
            reg = self.REG_PSC + self.timer
        else:
            reg = self.REG_PSC2 + self.timer - 4
        logger.debug(
            "[%s]: Set prescaler to PWM %s at timer %s to register: %s, global timer: %s",
            self._chan_desc,
            self._prescaler - 1,
            self.timer,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, self._prescaler - 1)

    def get_period(self) -> int:
        "Get the current PWM period value."
        return timer[self.timer]["arr"]

    def period(self, arr: int) -> None:
        """
        Set the PWM period value.

        The period defines the total number of clock ticks in one complete PWM cycle (both high and low pulses).
        A longer period results in a slower cycle, while a shorter period makes the PWM frequency faster.

        Args:
            arr: Auto-Reload Register (ARR). New period value (0-65535).

        ### Visual Representation

        The PWM signal can be illustrated as a repeating cycle of ON and OFF states.

        The Auto-Reload Register value determines how long the entire cycle takes:

        ```
        |<----------- Period (arr) ----------->|
        |                                      |
        |   High Time    |    Low Time         |
        |    (ON)        |     (OFF)           |
        |*************** |---------------------|
        ```

        - **Period**: Total duration of one cycle (High Time + Low Time), determined by `arr`.

        - **Frequency**: Number of cycles per second, calculated as `Frequency = Clock / arr`.

        Example:
            ```python
            pwm_controller.period(4095)  # Set period to 4095
            ```
        """
        global timer

        arr = round(arr)

        timer[self.timer]["arr"] = arr
        self._freq = self.CLOCK / self._prescaler / arr

        if self.timer < 4:
            reg = self.REG_ARR + self.timer
        else:
            reg = self.REG_ARR2 + self.timer - 4

        logger.debug(
            "[%s]: Set period to PWM %s at timer %s to register: %s, global timer: %s",
            self._chan_desc,
            arr,
            self.timer,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, arr)

    def get_pulse_width(self) -> int:
        "Get the currentpulse width."
        return self._pulse_width

    def pulse_width(self, pulse_width: Union[float, int]) -> None:
        """
        Set the pulse width.

        Args:
            pulse_width: Pulse width value (0-65535).

        Returns:
            float: The current pulse width value.
        """

        self._pulse_width = int(pulse_width)
        reg = self.REG_CHN + self.channel
        logger.debug(
            "[%s]: writing pulse width %s  to register: %s global timer: %s",
            self._chan_desc,
            self._pulse_width,
            hex(reg),
            timer,
        )
        self._i2c_write(reg, self._pulse_width)

    def get_pulse_width_percent(self) -> Optional[int]:
        "Get the current pulse width percentage if setted."
        if hasattr(self, "_pulse_width_percent"):
            return self._pulse_width_percent

    def pulse_width_percent(self, pulse_width_percent: int) -> None:
        """
        Set the pulse width percentage.

        Args:
            pulse_width_percent: Pulse width percentage (0-100).

        Returns:
            float: The current pulse width percentage.
        """
        global timer

        self._pulse_width_percent = pulse_width_percent
        temp = self._pulse_width_percent / 100.0
        pulse_width = temp * timer[self.timer]["arr"]
        self.pulse_width(pulse_width)


if __name__ == "__main__":
    import time

    speed = 70  # desired motor speed from 0 to 100
    motor_speed_pwm = PWM("P12")
    period = 4095
    prescaler = 10
    max_speed = 100
    pwm_speed = max(0, min(max_speed, int(speed / 2) + 50))  # 85
    motor_speed_pwm.pulse_width_percent(pwm_speed)
    print(f"motor moving={motor_speed_pwm.get_pulse_width_percent()}")
    time.sleep(2)  # move two seconds
    motor_speed_pwm.pulse_width_percent(0)  # stop
    print(f"motor stopped={motor_speed_pwm.get_pulse_width_percent()}")
