"""
A module to manage communication between a Raspberry Pi and devices that support the I2C protocol.

I2C stands for Inter-Integrated Circuit and is a type of synchronous
communication protocol, that allows multiple integrated circuits (ICs) to
communicate with one another using just two lines:

- **SCL (Clock line)**: Synchronizes the data transfer between the devices.
- **SDA (Data line)**: Carries the data between the devices.

#### How They Work
- **Master**: The device that initiates and controls the communication.
- **Slave**: The device that responds to the master's request.
- Each I2C device has a unique address that allows the master to communicate with specific devices.
"""

import logging
import os
from typing import Any, Callable, List, Optional, Protocol, Type, Union, cast

from robot_hat.data_types.bus import BusType
from robot_hat.exceptions import I2CAddressNotFound
from robot_hat.i2c.retry_decorator import RETRY_DECORATOR
from robot_hat.i2c.smbus_protocol import SMBusProtocol

_log = logging.getLogger(__name__)

SMBus: Optional[Type[SMBusProtocol]] = None


class I2CProbeBus(Protocol):
    """Minimum bus operations available to an address probe callback."""

    def read_byte(self, i2c_addr: int) -> int: ...

    def read_byte_data(self, i2c_addr: int, register: int) -> int: ...


I2CProbe = Callable[[I2CProbeBus, int], bool]


def read_byte_probe(bus: I2CProbeBus, address: int) -> bool:
    """Probe by reading one byte, without transmitting a data byte.

    This is less invasive than the legacy dummy write, but it is not
    universally side-effect-free. Prefer a device identity-register callback
    when the target protocol provides one.
    """
    bus.read_byte(address)
    return True


class I2C:
    """
    A class to manage communication between a Raspberry Pi and devices that
    support the I2C protocol. I2C stands for Inter-Integrated Circuit and is
    a type of synchronous communication protocol.

    ### Key Features:
    - Read and write functions for I2C communication.
    - Scan for connected I2C devices.
    - Retry mechanism for robust communication.

    #### What is I2C?
    I2C (Inter-Integrated Circuit) is a communication protocol that allows
    multiple integrated circuits (ICs) to communicate with one another using
    just two lines:
    - **SCL (Clock line)**: Synchronizes the data transfer between the devices.
    - **SDA (Data line)**: Carries the data between the devices.

    #### How They Work
    - **Master**: The device that initiates and controls the communication.
    - **Slave**: The device that responds to the master's request.
    - Each I2C device has a unique address that allows the master to communicate with specific devices.

    Here's a visual representation of scanning for devices:

    ```
         0 1 2 3 4 5 6 7 8 9 a b c d e f
    00:          -- -- -- -- -- -- -- -- -- -- -- --
    10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    70: -- -- -- -- 15 -- -- 17
    ```

    In the above scan, devices were found at addresses `0x15` and `0x17`.

    """

    def __init__(
        self,
        address: Union[int, List[int]],
        bus: BusType = 1,
        probe: Optional[I2CProbe] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the I2C bus.

        Args:
            address: The address or list of addresses of I2C devices.
            bus: I2C bus number. Default is 1.
            probe: Optional device-specific presence check. A single address is
                trusted without bus traffic when omitted. Address lists use a
                generic read probe when omitted because selecting one candidate
                necessarily requires a transaction.
        """
        global SMBus
        super().__init__(*args, **kwargs)
        self._closed = False

        if isinstance(bus, int):
            if SMBus is None:
                if os.getenv("ROBOT_HAT_MOCK_SMBUS") == "1":
                    from robot_hat.mock.smbus2 import MockSMBus as RealSMBus
                else:
                    from smbus2 import SMBus as RealSMBus
                SMBus = cast(Type[SMBusProtocol], RealSMBus)
            self._smbus = SMBus(bus)
            self._own_bus: bool = True
            _log.debug("Created own SMBus on bus %d", bus)
        else:
            self._smbus = bus
            self._own_bus = False
            _log.debug("Using injected SMBus instance")

        try:
            addr = self.find_address(address, probe=probe)
        except Exception:
            self.close()
            raise

        if addr is None:
            _log.error("I2C address %s not found", address)
            self.close()
            raise I2CAddressNotFound("I2C address not found")

        self._address: int = addr
        _log.debug(
            "I2C bus opened successfully at device address %s",
            self.address,
        )

    @property
    def address(self) -> int:
        return self._address

    def find_address(
        self,
        address: Union[int, List[int]],
        probe: Optional[I2CProbe] = None,
    ) -> Optional[int]:
        """
        Determine the appropriate I2C address for communication by either
        scanning for connected devices or verifying a given address.

        If a list of addresses is provided, probe them sequentially. A single
        configured address is trusted without generating bus traffic unless a
        probe callback is supplied.

        Returns the first available address or `None` if no valid address is found.
        """
        if isinstance(address, list):
            if not address:
                return None
            for addr in address:
                self._validate_address(addr)
                if self.check_address(addr, probe=probe) is not None:
                    return addr
        else:
            self._validate_address(address)
            if probe is None or self.check_address(address, probe=probe):
                return address
        return None

    @staticmethod
    def _validate_address(address: int) -> None:
        if isinstance(address, bool) or not isinstance(address, int):
            raise TypeError("I2C address must be an integer")
        if not 0x08 <= address <= 0x77:
            raise ValueError(
                "I2C address must be an unreserved 7-bit address (0x08-0x77)"
            )

    def check_address(
        self, addr: int, probe: Optional[I2CProbe] = None
    ) -> Union[int, None]:
        """Check whether an address acknowledges an explicit probe.

        The generic fallback performs a one-byte read. It avoids writing a
        dummy command but still cannot be guaranteed side-effect-free for every
        I²C device. Supply a device-specific probe whenever possible.
        """
        self._validate_address(addr)
        probe_fn = probe or read_byte_probe
        _log.debug("Probing I2C bus address 0x%02x", addr)
        try:
            if probe_fn(cast(I2CProbeBus, self._smbus), addr):
                _log.debug("Found I2C device at 0x%02x", addr)
                return addr
        except OSError as error:
            _log.debug("No I2C acknowledgement at 0x%02x: %s", addr, error)
        except Exception as error:
            _log.error("Unexpected error probing I2C address 0x%02x: %s", addr, error)
        return None

    @RETRY_DECORATOR
    def _write_byte(self, data: int) -> None:
        """
        Write a single byte to the I2C device.

        Args:
            data: Byte of data to write.

        Returns:
            None
        """
        _log.debug(
            "Writing a single byte to the I2C address %s Data: [0x%02X]",
            self.address,
            data,
        )
        self._smbus.write_byte(self.address, data)

    @RETRY_DECORATOR
    def _write_byte_data(self, reg: int, data: int) -> None:
        """
        Write a byte of data to a specific register.

        Args:
            reg: Register address.
            data: Byte of data to write.

        Returns:
            None
        """
        _log.debug(
            "Writing a byte of data on I2C address %s Register: [0x%02X] Data: [0x%02X]",
            hex(self.address),
            reg,
            data,
        )
        return self._smbus.write_byte_data(self.address, reg, data)

    @RETRY_DECORATOR
    def _write_word_data(self, reg: int, data: int) -> None:
        """
        Write a word of data to a specific register.

        Args:
            reg: Register address.
            data: Word of data to write.

        Returns:
            None
        """

        _log.debug(
            "Writing a single word (2 bytes) on I2C address %s Register: [0x%02X] Data: [0x%04X]",
            hex(self.address),
            reg,
            data,
        )
        return self._smbus.write_word_data(self.address, reg, data)

    @RETRY_DECORATOR
    def _write_i2c_block_data(self, reg: int, data: List[int]) -> None:
        """
        Write blocks of data to a specific register.

        Args:
            reg: Register address.
            data: List of data blocks to write.

        Returns:
            None
        """
        _log.debug(
            "Writing blocks of data on I2C address %s Register: [0x%02X] Data: %s",
            hex(self.address),
            reg,
            [f"0x{i:02X}" for i in data],
        )
        return self._smbus.write_i2c_block_data(self.address, reg, data)

    @RETRY_DECORATOR
    def _read_byte(self) -> int:
        """
        Read a single byte from the I2C device.

        Returns:
            int: Byte read from the device, or None if error.
        """

        result: int = self._smbus.read_byte(self.address)
        _log.debug(
            "Read a single byte on the I2C address %s Result: [0x%02X]",
            hex(self.address),
            result,
        )
        return result

    @RETRY_DECORATOR
    def _read_byte_data(self, reg: int) -> int:
        """
        Read a byte of data from a specific register.

        Args:
            reg: Register address.

        Returns:
            int: Byte read from the register, or None if error.
        """

        result = self._smbus.read_byte_data(self.address, reg)
        _log.debug(
            "Read a byte of data at register [0x%02X]. Result: [0x%02X]",
            reg,
            result,
        )
        return result

    @RETRY_DECORATOR
    def _read_word_data(self, reg: int) -> List[int]:
        """
        Read a word of data from a specific register.

        Args:
            reg: Register address.

        Returns:
            list: Word read from the register in two bytes, or None if error.
        """

        result: int = self._smbus.read_word_data(self.address, reg)
        result_list: List[int] = [result & 0xFF, (result >> 8) & 0xFF]

        _log.debug(
            "Read a word of data on the I2C address %s Register: [0x%02X] Result: [0x%04X]",
            self.address,
            reg,
            result,
        )
        return result_list

    @RETRY_DECORATOR
    def _read_i2c_block_data(self, reg: int, num: int) -> List[int]:
        """
        Read blocks of data from a specific register.

        Args:
            reg: Register address.
            num (int): Number of blocks to read.

        Returns:
            list: List of blocks read from the register.
        """

        result = self._smbus.read_i2c_block_data(self.address, reg, num)
        _log.debug(
            "Read blocks of data on the I2C address %s from a register [0x%02X] Result: [%s]",
            hex(self.address),
            reg,
            [f"0x{i:02X} " for i in result],
        )
        return result

    @RETRY_DECORATOR
    def is_ready(self) -> bool:
        """
        Check if the I2C device is ready.

        Returns:
            True if the I2C device is ready, False otherwise.
        """

        return self.check_address(self.address) is not None

    def scan(self, probe: Optional[I2CProbe] = None) -> List[int]:
        """
        Explicitly scan unreserved 7-bit addresses.

        Generic I²C discovery cannot be universally side-effect-free. The
        default read probe avoids transmitting the legacy dummy byte, but a
        device-specific identity probe is preferred.

        Returns:
            List of I2C addresses of devices found.
        """
        addresses: List[int] = []
        _log.debug("Scanning I2C bus for devices")

        if not self._smbus:
            _log.warning("SMBus not initialized. Unable to scan for I2C devices.")
            return addresses

        for address in range(0x08, 0x78):
            if self.check_address(address, probe=probe) is not None:
                addresses.append(address)

        _log.debug("Connected I2C devices: %s", ["0x%02x" % addr for addr in addresses])
        return addresses

    def write(self, data: Union[int, List[int], bytearray]) -> None:
        """
        Write data to the I2C device, with support for various data formats.

        This method delivers data over the I2C bus to the connected device. It is flexible in that
        it accepts an integer, a list of integers, or a bytearray. Based on the size of the
        provided data, this function internally delegates to the appropriate low-level I2C
        transmission method (_write_byte, _write_byte_data, _write_word_data, or _write_i2c_block_data).

        Data Interpretation Based on Input:
            - **Integer (int)**:
                - If it's a single byte (e.g., `0x00` to `0xFF`), it will be sent as a single byte.
                - If it's a multi-byte integer, it will be broken into 8-bit segments and transmitted as appropriate.
            - **List of integers (List[int])**: Interpreted as an array of sequential bytes. Depending on the length of the list:
                - 1 byte: Written as a single byte.
                - 2 bytes: The first byte is the register, and the second is the data byte.
                - 3+ bytes: The first byte is the register, and the remaining are sent as block data.
            - **Bytearray (bytearray)**: Treated as a list of bytes. The bytearray is converted to a list before transmission.

        Args:
            data: Input data to write. This can be:
                - An integer, which is either a single byte or a sequence of bytes.
                - A list of integers, where each integer represents a byte.
                - A bytearray, which is treated similarly to a list of bytes.

        Raises:
            ValueError: If the data cannot be processed as an integer, list, or bytearray.

        I2C Handling Logic:
            - If the data length is 1: Write a single byte using `_write_byte`.
            - If the data length is 2: Write a register and a corresponding byte using `_write_byte_data`.
            - If the data length is 3: Write a register and a 16-bit word (2 bytes) using `_write_word_data`.
            - If the data is 4 bytes or more: Write a block of data using `_write_i2c_block_data`.

        Example:
            For a register `0x10`, writing the value `0xABCD` could be done through:

            ```python
            self.write([0x10, 0xCD, 0xAB])  # Calls _write_word_data with reg=0x10, data=0xABCD
            ```

        Returns:
            None
        """

        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, int):
            # Convert integer (could be multi-byte) input into a list of bytes, lowest first
            if data == 0:
                data_all = [0]
            else:
                data_all: List[int] = []
                while data > 0:
                    data_all.append(data & 0xFF)  # Append the least significant byte
                    data >>= 8  # Shift right to prepare for the next byte
        elif isinstance(data, list):
            data_all = data

        data_len = len(data_all)

        if data_len == 1:
            data = data_all[0]
            self._write_byte(data)
        elif data_len == 2:
            # Two-byte write where first item is register, second item is the value
            reg = data_all[0]
            data = data_all[1]
            self._write_byte_data(reg, data)
        elif data_len == 3:
            # Three-byte write: first byte is the register, next two bytes form a 16-bit word
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, data)
        else:
            # For more than 3 bytes: block write (first byte is the register, rest is data)
            reg = data_all[0]
            data = list(
                data_all[1:]
            )  # All bytes after the first are written as block data
            self._write_i2c_block_data(reg, data)

    def read(self, length: int = 1) -> List[int]:
        """
        Read a specified number of bytes from the I2C device.

        This method reads data from the I2C device using the `_read_byte()` method,
        which retrieves one byte at a time. The number of bytes to read is determined
        by the `length` parameter. The method accumulates these bytes into a list and
        returns them. If a read operation fails (i.e., returns `None`), a warning
        message is logged, but the method will continue reading subsequent bytes.

        Args:
            length: The number of bytes to read from the I2C device. The length must be a positive integer.

        Returns:
            list: A list containing `length` bytes read from the device. If any read
                  operation fails and returns `None`, the list may have fewer bytes
                  than requested or exclude erroneous values.

        Raises:
            ValueError: If `length` is non-positive or invalid.

        Operation Details:
            - The method reads one byte at a time by calling the internal `_read_byte()` function.
            - In the event that `_read_byte()` returns `None`, this indicates a failure to read
              a byte from the device. In such cases, a warning is logged, showing how many bytes
              successfully read before encountering the issue.
            - The overall process continues even if one or more failures occur, and the result
              returns the bytes that were successfully read.

        Logging:
            - If the read operation fails for any byte (i.e., `_read_byte()` returns `None`),
              the method logs a warning like:
              `Read {i} byte of ({length}) from the I2C address {self.address} is None`

        Example:
            ```python
            data = self.read(3)  # Reads 3 bytes from the I2C device
            print(data)          # Output: [0x01, 0xA9, 0x34] (example bytes)
            ```

        Note:
            Some implementations of `_read_byte()` might return `None` in case of hardware
            communication errors or timeouts. Therefore, you should be prepared to handle
            incomplete results.
        """

        result: List[int] = []
        for _ in range(length):
            byte: int = self._read_byte()
            result.append(byte)
        return result

    def mem_write(self, data: Union[int, List[int], bytearray], memaddr: int) -> None:
        """
        Write data to a specific memory address (register) on the I2C device.

        This method allows writing data directly to a specific memory address, such as a register
        within the I2C device. The memory address (`memaddr`) determines where the data should
        be stored on the device. The function supports multiple input data types (int, list of
        integers, or bytearray) and converts these inputs into a sequence of bytes to be transferred.

        Args:
            data: The data to write. This can be:
                - A single integer: It can represent one or more bytes (0xFFFF is 2 bytes: [0xFF, 0xFF]).
                - A list of integers: Each integer represents a byte (e.g., `[0x12, 0x34]`).
                - A bytearray: Treated similarly to a list of bytes.

            memaddr (int): The register (memory address) of the device where the data will be written.

        Raises:
            ValueError: If the data is not an integer, list of integers, or bytearray.

        Processing the Input Data:
            - **Integers**: If the input is an integer, it is split into individual bytes
              before being sent. For example, the integer `0x1234` will be split into
              two bytes `[0x12, 0x34]` and transmitted separately.
            - **Lists and Bytearrays**: These are treated as sequences of bytes and directly
              passed on for transmission.

        Transfer Details:
            The data is written to the specified `memaddr` register using the internal method
            `_write_i2c_block_data()`.

        Example:
            To write `0x1234` to register `0x10`:
            ```python
            self.mem_write(0x1234, 0x10)
            # Transmits [0x10] register and [0x12, 0x34] as the 16-bit data
            ```

        Returns:
            None
        """

        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, list):
            data_all = data
        elif isinstance(data, int):
            data_all: List[int] = []
            if data == 0:
                data_all = [0]
            else:
                while data > 0:
                    data_all.append(data & 0xFF)  # Append the least significant byte
                    data >>= 8  # Shift right to prepare for the next byte
        self._write_i2c_block_data(memaddr, data_all)

    def mem_read(self, length: int, memaddr: int) -> List[int]:
        """
        Read data from a specific memory address (register) on the I2C device.

        This method reads a specified number of bytes from a given memory address (register)
        on the I2C device. The address `memaddr` is an internal register or memory location
        on the device from which `length` bytes will be fetched. The method will log any errors
        encountered during the read operation.

        Args:
            length: The number of bytes to read from the specified memory address.
            memaddr: The register (address) from which to read data.

        Returns:
            Returns a list of bytes read from the register. If an error occurs,
            this method will log an error and return `None`.

        Transfer Details:
            - The method reads `length` bytes starting from `memaddr` using the internal
              `_read_i2c_block_data()` method, which interacts with the underlying I2C
              communication system.
            - If the read is successful, it will store the data in a list and return it.
              Otherwise, it will log an error message if the read fails and return `None`.

        Logging:
            On a successful read, the result is logged along with descriptions for the
            memory and value. For example:
            ```plaintext
            Read data from I2C address 0x50, Register [0x10]: Result: [0x12 'desc1', 0x34 'desc2']
            ```

            If a read fails, an error message is logged:
            ```plaintext
            Failed to read data from I2C address 0x50, Register [0x10]
            ```

        Example:
            To read 4 bytes from register `0x10`:
            ```python
            data = self.mem_read(4, 0x10)
            # Example output: [0x12, 0x34, 0x56, 0x78]
            ```

        Returns:
            A list of bytes read from the specified register.
        """

        result = self._read_i2c_block_data(memaddr, length)
        if result is None:
            _log.error(
                "Failed to read data from I2C address %s, register [0x%02X]",
                self.address,
                memaddr,
            )
        else:
            _log.debug(
                "Read data from I2C address %s, Register [0x%02X] Result: %s",
                self.address,
                memaddr,
                [f"0x{i:02X}" for i in result],
            )

        return result

    def is_available(self, probe: Optional[I2CProbe] = None) -> bool:
        """Return whether the configured address acknowledges an explicit probe."""
        return self.check_address(self.address, probe=probe) is not None

    def close(self) -> None:
        """
        Close the I2C bus connection if this instance owns the SMBus object.

        For external SMBus instances, no closure is performed.
        """
        if getattr(self, "_closed", True):
            return
        smbus = getattr(self, "_smbus", None)
        if getattr(self, "_own_bus", False) and smbus is not None:
            smbus.close()
        self._closed = True

    def __del__(self) -> None:
        """
        Destructor method. Closes the I2C bus connection if this instance owns it.
        """
        self.close()
