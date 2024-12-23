"""
This module provides a class for interfacing with an ADXL345 accelerometer sensor using I2C.
"""

from typing import List, Optional, Union

from .i2c import I2C


class ADXL345(I2C):
    """
    This class provides interface for an ADXL345 accelerometer sensor using I2C.

    The ADXL345 is a small 3-axis accelerometer with high resolution (13-bit) measurement at up to ±16g.

    Example:
    --------------

    ```python
    adxl = ADXL345()
    x, y, z = adxl.read()  # Reads all axis data
    x_value = adxl.read(ADXL345.X)  # Reads X-axis data
    ```
    """

    X = 0
    """The X-axis."""

    Y = 1
    """The Y-axis"""

    Z = 2
    """The Z-axis"""

    ADDR = 0x53
    """Default I2C address for the ADXL345 """

    _REG_DATA_X = 0x32
    """Register address for X-axis data."""

    _REG_DATA_Y = 0x34
    """Register address for Y-axis data."""

    _REG_DATA_Z = 0x36
    """Register address for Z-axis data."""

    _REG_POWER_CTL = 0x2D
    """Register address for power control."""

    _AXISES = [_REG_DATA_X, _REG_DATA_Y, _REG_DATA_Z]
    """List of register addresses for X, Y, Z axis data."""

    def __init__(self, *args, address: int = ADDR, bus: int = 1, **kwargs):
        """
        Initializes the ADXL345 sensor.

        Args:

        - address: The address of I2C device.
        - bus: I2C bus number.
        """
        super().__init__(address=address, bus=bus, *args, **kwargs)
        self.address = address

    def read_axis(
        self, axis: Optional[int] = None
    ) -> Union[float, List[Union[float, None]], None]:
        """
        Reads the specified axis data or all axis data.

        Args:
        axis: The axis to read (X=0, Y=1, Z=2). If None, data for all axes will be read.
        """
        if axis is None:
            return [self._read(i) for i in range(3)]
        else:
            return self._read(axis)

    def _read(self, axis: int) -> Union[float, None]:
        """
        Reads data from a specified axis register.
        """
        raw_2 = 0
        result = super().read()
        data = (0x08 << 8) + self._REG_POWER_CTL
        if result:
            self.write(data)
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw = self.mem_read(2, self._AXISES[axis])
        # The first value read is always 0, so read it again.
        self.mem_write(0, 0x31)
        self.mem_write(8, 0x2D)
        raw = self.mem_read(2, self._AXISES[axis])
        if raw:
            if raw[1] >> 7 == 1:
                raw_1 = raw[1] ^ 128 ^ 127
                raw_2 = (raw_1 + 1) * -1
            else:
                raw_2 = raw[1]
            g = raw_2 << 8 | raw[0]
            value = g / 256.0
            return value
