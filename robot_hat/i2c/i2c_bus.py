import logging
import os
from types import TracebackType
from typing import TYPE_CHECKING, List, Optional, Sequence, Type, Union, cast

from robot_hat.common.event_emitter import EventEmitter
from robot_hat.i2c.retry_decorator import RETRY_DECORATOR
from robot_hat.i2c.smbus_protocol import SMBusProtocol
from robot_hat.interfaces.smbus_abc import SMBusABC

if TYPE_CHECKING:
    from smbus2 import i2c_msg


_log = logging.getLogger(__name__)

SMBus: Optional[Type[SMBusProtocol]] = None


class I2CBus(SMBusABC):
    """
    SMBus/I²C bus wrapper using an underlying SMBus implementation.

    Provides retry logic for operations, event emission on close, and a thin
    compatibility layer over the underlying smbus2 (or mock) object.
    """

    def __init__(self, bus: Union[str, int], force: bool = False) -> None:
        """
        Create and initialize the I2C bus wrapper.

        Args:
            bus: Bus identifier to open.
            force: Whether to open/operate in force mode.
        """
        global SMBus

        if SMBus is None:
            if os.getenv("ROBOT_HAT_MOCK_SMBUS") == "1":
                from robot_hat.mock.smbus2 import MockSMBus as RealSMBus
            else:
                from smbus2 import SMBus as RealSMBus
            SMBus = cast(Type[SMBusProtocol], RealSMBus)

        self._bus = bus
        self._smbus = SMBus(bus, force)
        self.emitter = EventEmitter()
        _log.debug("SMBus initialized on bus %s with force=%s", bus, force)

    def open(self, bus: Union[int, str]) -> None:
        """
        Open or re-open the underlying SMBus device.

        Args:
            bus: Bus identifier to open.
        """
        _log.debug("Opening SMBus on bus %s", bus)
        if hasattr(self._smbus, "open"):
            self._smbus.open(bus)
        else:
            _log.warning("Underlying SMBus instance does not support 'open'.")

    def close(self) -> None:
        """
        Close the underlying SMBus and emit a 'close' event.

        Any errors raised by the underlying close are logged. The close event
        is emitted and then removed from the emitter.
        """
        _log.debug("Closing SMBus on bus %s", self._bus)
        try:
            self._smbus.close()
        except TimeoutError as err:
            _log.error("Timeout closing SMBus '%s': %s", self._bus, err)
        except OSError as err:
            _log.error("OS Error closing SMBus '%s': %s", self._bus, err)
        except Exception:
            _log.error("Unexpected error closing SMBus '%s'", self._bus, exc_info=True)
        finally:
            self.emitter.emit("close", self)
            self.emitter.off("close")

    @RETRY_DECORATOR
    def enable_pec(self, enable: bool = False) -> None:
        """
        Enable or disable Packet Error Checking (PEC) on the bus.

        Args:
            enable: Whether to enable PEC.
        """
        _log.debug("Setting PEC to %s", enable)
        self._smbus.enable_pec(enable)

    @RETRY_DECORATOR
    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        """
        Perform an SMBus 'write quick' to probe or toggle device state.

        Args:
            i2c_addr: Target device address.
            force: Optional override for force behavior.
        """
        _log.debug("write_quick: addr=%s, force=%s", i2c_addr, force)
        self._smbus.write_quick(i2c_addr, force)

    @RETRY_DECORATOR
    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        """
        Read and return a single byte from a device (no register)..

        Args:
            i2c_addr: Target device address.
            force: Optional override for force behavior.

        Returns:
            The byte value read from the device.
        """
        _log.debug("read_byte: addr=%s, force=%s", i2c_addr, force)
        result = self._smbus.read_byte(i2c_addr, force)
        _log.debug("read_byte result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a single byte to a device (no register).

        Args:
            i2c_addr: Target device address.
            value: Byte value to write.
            force: Optional override for force behavior.
        """
        _log.debug("write_byte: addr=%s, value=%s, force=%s", i2c_addr, value, force)
        self._smbus.write_byte(i2c_addr, value, force)

    @RETRY_DECORATOR
    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        """
        Read and return a byte from a specific device register.

        Args:
            i2c_addr: Target device address.
            register: Register address to read from.
            force: Optional override for force behavior.

        Returns:
            The byte value read from the register.
        """
        _log.debug(
            "Read_byte_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_byte_data(i2c_addr, register, force)
        _log.debug("read_byte_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a byte to a specific device register.

        Args:
            i2c_addr: Target device address.
            register: Register address to write to.
            value: Byte value to write.
            force: Optional override for force behavior.
        """
        _log.debug(
            "write_byte_data: addr=%s, register=%s, value=%s, force=%s",
            i2c_addr,
            register,
            value,
            force,
        )
        self._smbus.write_byte_data(i2c_addr, register, value, force)

    @RETRY_DECORATOR
    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        """
        Read and return a 16-bit word from a device register.

        Args:
            i2c_addr: Target device address.
            register: Register address to read from.
            force: Optional override for force behavior.

        Returns:
            The word value read from the register.
        """
        _log.debug(
            "read_word_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_word_data(i2c_addr, register, force)
        _log.debug("read_word_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        """
        Write a 16-bit word to a device register.

        Args:
            i2c_addr: Target device address.
            register: Register address to write to.
            value: Word value to write.
            force: Optional override for force behavior.
        """
        _log.debug(
            "write_word_data: addr=%s, register=%s, value=%s, force=%s",
            i2c_addr,
            register,
            value,
            force,
        )
        self._smbus.write_word_data(i2c_addr, register, value, force)

    @RETRY_DECORATOR
    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> int:
        """
        Perform an SMBus process call: write then read back in one transaction.

        Args:
            i2c_addr: Target device address.
            register: Register for the process call.
            value: Value to send with the call.
            force: Optional override for force behavior.

        Returns:
            The response returned by the device.
        """
        _log.debug(
            "process_call: addr=%s, register=%s, value=%s, force=%s",
            i2c_addr,
            register,
            value,
            force,
        )
        result = self._smbus.process_call(i2c_addr, register, value, force)
        _log.debug("process_call result: %s", result)
        return result

    @RETRY_DECORATOR
    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        """
        Read a block of bytes from a device register.

        Args:
            i2c_addr: Target device address.
            register: Register address to read from.
            force: Optional override for force behavior.

        Returns:
            A list of byte values returned by the device.
        """
        _log.debug(
            "read_block_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_block_data(i2c_addr, register, force)
        _log.debug("read_block_data result: %s", result)
        return result

    @RETRY_DECORATOR
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
            i2c_addr: Target device address.
            register: Register address to write to.
            data: Sequence of byte values to send.
            force: Optional override for force behavior.
        """
        _log.debug(
            "write_block_data: addr=%s, register=%s, data=%s, force=%s",
            i2c_addr,
            register,
            data,
            force,
        )
        self._smbus.write_block_data(i2c_addr, register, data, force)

    @RETRY_DECORATOR
    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> List[int]:
        """
        Perform a block process call: write a block and read a block response.

        Args:
            i2c_addr: Target device address.
            register: Register for the block process call.
            data: Sequence of bytes to send.
            force: Optional override for force behavior.

        Returns:
            The block of data returned by the device.
        """
        _log.debug(
            "block_process_call: addr=%s, register=%s, data=%s, force=%s",
            i2c_addr,
            register,
            data,
            force,
        )
        result = self._smbus.block_process_call(i2c_addr, register, data, force)
        _log.debug("block_process_call result: %s", result)
        return result

    @RETRY_DECORATOR
    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        """
        Read a specified number of bytes from a device using I2C block read.

        Args:
            i2c_addr: Target device address.
            register: Register address to read from.
            length: Number of bytes to read.
            force: Optional override for force behavior.

        Returns:
            A list of byte values read from the device.
        """
        _log.debug(
            "read_i2c_block_data: addr=%s, register=%s, length=%s, force=%s",
            i2c_addr,
            register,
            length,
            force,
        )
        result = self._smbus.read_i2c_block_data(i2c_addr, register, length, force)
        _log.debug("read_i2c_block_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        """
        Write a sequence of bytes to a device using I2C block write.

        Args:
            i2c_addr: Target device address.
            register: Register address to write to.
            data: Sequence of byte values to send.
            force: Optional override for force behavior.
        """
        _log.debug(
            "write_i2c_block_data: addr=%s, register=%s, data=%s, force=%s",
            i2c_addr,
            register,
            data,
            force,
        )
        self._smbus.write_i2c_block_data(i2c_addr, register, data, force)

    @RETRY_DECORATOR
    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        """
        Perform raw combined I2C read/write transactions.

        Args:
            *i2c_msgs: One or more message objects describing the transactions.
        """
        _log.debug("i2c_rdwr: messages=%s", i2c_msgs)
        return self._smbus.i2c_rdwr(*i2c_msgs)

    def __enter__(self) -> "I2CBus":
        _log.debug("Entering I2CBus context manager")
        self._smbus.__enter__()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        """
        Exit context manager and perform cleanup by delegating to the SMBus.
        """
        _log.debug("Exiting I2CBus context manager")
        self._smbus.__exit__(exc_type=exc_type, exc_val=exc_val, exc_tb=exc_tb)
