"""
A module to manage the Analog-to-Digital Converter (ADC).
"""

import logging
from typing import List, Union

from robot_hat.exceptions import InvalidChannel
from robot_hat.i2c.i2c_manager import I2C

logger = logging.getLogger(__name__)


ADC_DEFAULT_ADDRESSES = [0x14, 0x15]

ADC_MAX_CHAN_VAL = 7
ADC_ALLOWED_CHANNELS = list(range(0, ADC_MAX_CHAN_VAL))
ADC_ALLOWED_CHANNELS_PIN_NAMES = [f"A{val}" for val in ADC_ALLOWED_CHANNELS]

ADC_ALLOWED_CHANNELS_DESCRIPTION = "Channel should be one of: " + ", ".join(
    ADC_ALLOWED_CHANNELS_PIN_NAMES + [f"{num}" for num in ADC_ALLOWED_CHANNELS]
)


class ADC(I2C):
    """
    A class to manage the Analog-to-Digital Converter (ADC).

    Key Concepts:
    --------------
    - Channel: Each sensor or input signal is connected to an ADC channel.
    - Resolution: Determines how accurately the analog signal is converted to
      digital. A 12-bit ADC, for instance, could represent an analog signal with
      a value between 0 and 4095.
    - MSB (Most Significant Byte): The byte in the data that has the highest
      value, representing the upper part of a numerical value.
    - LSB (Least Significant Byte): The byte in the data that has the lowest
      value, representing the lower part of a numerical value.

    Example
    --------------
    ```python
    from robot_hat import SunfounderADC

    # Initialize ADC on channel A0
    adc = SunfounderADC(channel="A4")

    # Read the ADC value
    value = adc.read()
    print(f"ADC Value: {value}")

    # Read the voltage
    voltage = adc.read_voltage()
    print(f"Voltage: {voltage} V")

    ```
    """

    def __init__(
        self,
        channel: Union[str, int],
        address: Union[int, List[int]] = ADC_DEFAULT_ADDRESSES.copy(),
        *args,
        **kwargs,
    ) -> None:
        """
        Initialize the ADC.

        Args:
            channel: Channel number (0-7 or A0-A7).
            address: The address or list of addresses of I2C devices.
        """

        super().__init__(address, *args, **kwargs)
        if self.address is not None:
            logger.debug(f"ADC device address: 0x{self.address:02X}")
        else:
            logger.error("ADC device address not found")

        normalized_channel = self._normalize_channel(channel)
        channel_reg = self._channel_to_register(normalized_channel)

        # Preserve the legacy public attribute while tracking helpers internally.
        self._channel_index = normalized_channel
        self._channel_reg = channel_reg
        self.channel = channel_reg

    @staticmethod
    def _normalize_channel(channel: Union[str, int]) -> int:
        """Convert channel identifiers (e.g. "A4") to an integer index."""
        if (
            channel not in ADC_ALLOWED_CHANNELS_PIN_NAMES
            and channel not in ADC_ALLOWED_CHANNELS
        ):
            raise InvalidChannel(
                f"Invalid ADC channel {channel}. " + ADC_ALLOWED_CHANNELS_DESCRIPTION
            )

        if isinstance(channel, str):
            return int(channel[1:])
        return int(channel)

    @staticmethod
    def _channel_to_register(channel_index: int) -> int:
        """Translate a channel index into the device register value."""
        return (ADC_MAX_CHAN_VAL - channel_index) | 0x10

    def _read_raw_value_for_reg(self, channel_reg: int) -> int:
        """Read a raw ADC value for the provided register selector."""
        self.write([channel_reg, 0, 0])

        msb, lsb = self.read(2)  # read two bytes

        logger.debug(
            "ADC Most Significant Byte: '%s', Least Significant Byte: '%s'", msb, lsb
        )

        value = (msb << 8) + lsb
        logger.debug("ADC combined value: '%s'", value)
        return value

    def read_raw_value(self) -> int:
        """
        Retrieve and combine the ADC's Most Significant Byte (MSB) and Least Significant Byte (LSB).

        Returns:
            int: ADC value (0-4095).
        """
        return self._read_raw_value_for_reg(self._channel_reg)

    def read_raw_value_channel(self, channel: Union[str, int]) -> int:
        """Read the raw ADC value from a different channel without re-instantiating."""
        channel_index = self._normalize_channel(channel)
        channel_reg = self._channel_to_register(channel_index)
        return self._read_raw_value_for_reg(channel_reg)

    def read_voltage(self) -> float:
        """
        Read the ADC value and convert to voltage.

        Returns:
            float: Voltage value (0-3.3 V).
        """
        value = self.read_raw_value()
        voltage = value * 3.3 / 4095
        logger.debug(f"ADC raw voltage: {voltage}")
        return voltage

    def read_voltage_channel(self, channel: Union[str, int]) -> float:
        """Read and convert the voltage for a specific channel."""
        value = self.read_raw_value_channel(channel)
        voltage = value * 3.3 / 4095
        logger.debug("ADC raw voltage on channel %s: %s", channel, voltage)
        return voltage
