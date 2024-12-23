"""
Grayscale Module provides 3-channel grayscale sensing, allowing for the
detection of line status or intensity using three individual ADC channels.
"""

import logging
from typing import List, Optional

from .adc import ADC
from .exceptions import GrayscaleTypeError

logger = logging.getLogger(__name__)


class Grayscale:
    """
    Grayscale class provides 3-channel grayscale sensing, allowing for the
    detection of line status or intensity using three individual ADC channels.

    ### Example usage

    ```python
    from robot_hat.adc import ADC
    from robot_hat.grayscale import Grayscale

    # Initialize ADC channels
    pin0 = ADC(0)  # Initialize ADC object for channel 0
    pin1 = ADC(1)  # Initialize ADC object for channel 1
    pin2 = ADC(2)  # Initialize ADC object for channel 2

    # Initialize Grayscale module with ADC pins and a reference (optional)
    grayscale = Grayscale(pin0, pin1, pin2, reference=[900, 900, 900])

    # Set reference manually
    grayscale.reference = [1000, 1000, 1000]

    # Get the status of all lines
    status = grayscale.read_status()
    print(f"Line statuses: {status}")

    # Read the grayscale value from the left channel
    left_value = grayscale.read(Grayscale.LEFT)
    print(f"Left channel value: {left_value}")

    # Read grayscale values for all channels
    all_values = grayscale.read_all()
    print(f"All channel values: {all_values}")
    ```
    """

    LEFT = 0
    """Left Channel"""
    MIDDLE = 1
    """Middle Channel"""
    RIGHT = 2
    """Right Channel"""

    _reference = [1000, 1000, 1000]

    def __init__(
        self, pin0: ADC, pin1: ADC, pin2: ADC, reference: List[int] = [1000, 1000, 1000]
    ):
        """
        Initializes a Grayscale module with three ADC channels and optional reference values.

        Args:
            pin0 (ADC): ADC object for the left channel.
            pin1 (ADC): ADC object for the middle channel.
            pin2 (ADC): ADC object for the right channel.
            reference (List[int], optional): Default reference values for black/white thresholds
                for the three channels. Defaults to [1000, 1000, 1000].

        Raises:
            GrayscaleTypeError: If the ADC objects are not valid.
        """
        self.pins = (pin0, pin1, pin2)
        for i, pin in enumerate(self.pins):
            if not isinstance(pin, ADC):
                msg = f"Invalid Pin{i}: must be ADC instance"
                logger.error(msg)
                raise GrayscaleTypeError(msg)
        self.reference = reference

    @property
    def reference(self) -> List[int]:
        """
        Retrieves the reference values for the grayscale sensors.

        The reference values are used to distinguish between black and white in
        the `read_status` method. Each channel has its own reference value that
        sets the threshold for determining line status.

        Returns:
            The current reference values for the three channels, in the order: [LEFT, MIDDLE, RIGHT].
        """
        return self._reference

    @reference.setter
    def reference(self, value: List[int]):
        """
        Sets the reference values for the grayscale sensors.

        The reference values determine the threshold between black and white for
        the three channels. Each reference value should correspond to one of the
        channels (LEFT, MIDDLE, RIGHT). The values must be provided as a list
        containing exactly three integers.

        Args:
            value: A list of three integers representing the reference values for each of the channels.

        Raises:
            GrayscaleTypeError: If the input is not a list of three integers.

        Example:
            >>> grayscale.reference = [950, 960, 970]  # Set new reference values
            >>> print(grayscale.reference)            # Output: [950, 960, 970]
        """
        if not isinstance(value, list) or len(value) != 3:
            raise GrayscaleTypeError(
                "Reference value must be a list of three integers."
            )

        self._reference = value

    def read_status(self, datas: Optional[List[int]] = None) -> List[int]:
        """
        Reads the status of the lines based on current reference values. Status is
        calculated as 0 for white and 1 for black.

        Args:
            datas (Optional[List[int]], optional): List of grayscale data to process.
                If not provided, grayscale data is read directly from the sensors.

        Returns:
            A list of statuses for each channel, where 0 represents white
            and 1 represents black.

        Raises:
            GrayscaleTypeError: If the reference values are not set.
        """
        if self._reference == None:
            raise GrayscaleTypeError("Reference value is not set")
        if datas == None:
            datas = self.read_all()
        return [0 if data > self._reference[i] else 1 for i, data in enumerate(datas)]

    def read_all(self) -> List[int]:
        """
        Reads grayscale intensity values from all three channels.

        Returns:
            A list of grayscale intensity values for all channels.
        """
        result: List[int] = []
        for pin in self.pins:
            val = pin.read()
            result.extend(val)

        return result

    def read(self, channel: Optional[int] = None) -> List[int]:
        """
        Reads grayscale data from a specific channel or all channels.

        Args:
            channel (Optional[int], optional): Channel to read from. If not provided,
                data from all channels is returned.

                - `Grayscale.LEFT`: Left channel (index 0).
                - `Grayscale.MIDDLE`: Middle channel (index 1).
                - `Grayscale.RIGHT`: Right channel (index 2).

        Returns:
            A list of grayscale intensity values for the specified channel
            or all channels.
        """
        if channel == None:
            return self.read_all()
        else:
            return self.pins[channel].read()
