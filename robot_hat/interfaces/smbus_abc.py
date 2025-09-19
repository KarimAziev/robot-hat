"""
Abstract base class defining an SMBus/I²C interface.

This module defines `SMBusABC`, an abstract base class that specifies the
interface expected for SMBus/I²C communication implementations used by
robot_hat. Concrete implementations should subclass SMBusABC and implement
all abstract methods to provide platform-specific behavior (for example,
wrapping smbus2 or direct ioctl use).
"""

from abc import ABC, abstractmethod
from types import TracebackType
from typing import TYPE_CHECKING, List, Optional, Sequence, Type, Union

if TYPE_CHECKING:
    from smbus2 import I2cFunc, i2c_msg


class SMBusABC(ABC):
    """
    Abstract SMBus / I²C interface.

    Attributes:
        fd: File descriptor or handle for the open bus device,
            if applicable. Implementations may set this to None when closed.
        funcs: Bitfield of supported I²C functionality flags
            (see smbus2.I2cFunc). Concrete implementations should populate
            this after opening the bus if such information is available.
        address: Current I²C slave address configured on the bus handle, if applicable.
        force: Default behavior for operations that accept an optional
            `force` parameter. When True, operations may use a "force" mode
            (for example, bypassing kernel driver checks) when addressing
            an I²C device. Behavior is backend-dependent.
        pec: Packet Error Checking (PEC) enable state. Typically 0 or 1,
            backend-dependent.
    """

    fd: Optional[int]
    funcs: "I2cFunc"
    address: Optional[int]
    force: bool
    pec: int

    @abstractmethod
    def __init__(self, bus: Union[None, int, str] = None, force: bool = False) -> None:
        pass

    @abstractmethod
    def __enter__(self) -> "SMBusABC":
        """
        Enter a context manager for the SMBus handle.

        Returns: The bus instance (usually `self`), ready for use.
        """
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Exit the context manager, performing cleanup.

        Implementations should close the underlying bus or release resources.
        Exceptions propagated from the context block are provided but handling
        them is implementation- or caller-dependent.
        """
        pass

    @abstractmethod
    def open(self, bus: Union[int, str]) -> None:
        """
        Open an SMBus/I²C device.

        Args:
            bus: Bus identifier to open. This is typically an integer bus number
            (e.g. 1) or a device path string (e.g. "/dev/i2c-1"), depending on
            the implementation.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Close the SMBus/I²C device and release any associated resources.
        """
        pass

    @abstractmethod
    def enable_pec(self, enable: bool = False) -> None:
        """
        Enable or disable Packet Error Checking (PEC).
        """
        pass

    @abstractmethod
    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        """
        Perform an SMBus "write quick" operation to the given address.

        This is a very small/low-level operation that typically toggles the
        read/write bit and is used as a probe in some contexts.

        Args:
            i2c_addr: 7-bit I²C device address.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.
        """
        pass

    @abstractmethod
    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        """
        Read a single byte from a device (no register).

        Args:
            i2c_addr: 7-bit I²C device address.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns: The byte read (0-255).
        """

        pass

    @abstractmethod
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a single byte to a device (no register).

        Args:
            i2c_addr: 7-bit I²C device address.
            value: Byte value to write (0-255).
            force: If provided, overrides the instance's
                default `force` behavior for this operation.
        """
        pass

    @abstractmethod
    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        """
        Read a single byte from a specified register of the device.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to read from.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns:
            int: The byte read (0-255).
        """

        pass

    @abstractmethod
    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a single byte to a specified register of the device.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to write to.
            value: Byte value to write (0-255).
            force: If provided, overrides the instance's
                default `force` behavior for this operation.
        """

        pass

    @abstractmethod
    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        """
        Read a 16-bit word from a specified register of the device.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to read from.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns:
            The word read (0-65535), endianness is backend-dependent
                 (usually little-endian for SMBus word operations).
        """

        pass

    @abstractmethod
    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a 16-bit word to a specified register of the device.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to write to.
            value: Word value to write (0-65535).
            force: If provided, overrides the instance's
                default `force` behavior for this operation.
        """

        pass

    @abstractmethod
    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> int:
        """
        Perform an SMBus "process call" operation.

        This operation writes a 16-bit value to a register and reads back
        a 16-bit response in a single transaction.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register for the process call.
            value: 16-bit value to send with the call.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns a 16-bit response in a single transaction.
        """

        pass

    @abstractmethod
    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        """
        Read a block of up to 32 bytes from a device register.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to read from.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns: A list of byte values read (each 0-255).
        """

        pass

    @abstractmethod
    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        """
        Write a block of data to a device register.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to write to.
            data: Sequence of byte values (each 0-255) to write.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Raises:
            OSError: On low-level I/O errors.
        """

        pass

    @abstractmethod
    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> List[int]:
        """
        Perform an SMBus block process call.

        This writes a block of data to the device and reads back a block
        response in a single transaction.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register for the block process call.
            data: Sequence of bytes to send.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns:
            List[int]: The block of data returned by the device.

        Raises:
            OSError: On low-level I/O errors.
        """

        pass

    @abstractmethod
    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        """
        Read a specified number of bytes from a device register using an I2C
        block read.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to read from.
            length: Number of bytes to read.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.

        Returns:
            A list of byte values read (each 0-255), of length up
                to `length` (or less if the device returns fewer bytes).
        """

        pass

    @abstractmethod
    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        """
        Write a sequence of bytes to a device register using an I2C block
        write.

        Args:
            i2c_addr: 7-bit I²C device address.
            register: Register address to write to.
            data: Sequence of byte values to write.
            force: If provided, overrides the instance's
                default `force` behavior for this operation.
        """

        pass

    @abstractmethod
    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        """
        Perform raw combined I2C read/write transactions.

        Accepts one or more i2c_msg objects (as provided by smbus2 or an
        equivalent backend) to perform combined transactions in a single
        ioctl/syscall.

        Args:
            *i2c_msgs: One or more message objects representing the
                sequence of read and write operations to perform.
        """

        pass
