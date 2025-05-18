import logging
import os
from types import TracebackType
from typing import TYPE_CHECKING, List, Optional, Sequence, Type, Union

from robot_hat.common.event_emitter import EventEmitter
from robot_hat.i2c.retry_decorator import RETRY_DECORATOR
from robot_hat.interfaces.smbus_abc import SMBusABC

USE_MOCK = os.getenv("ROBOT_HAT_MOCK_SMBUS")

if USE_MOCK != "1":
    from smbus2 import SMBus as SMBus2
else:
    from robot_hat.mock.smbus2 import MockSMBus as SMBus2


if TYPE_CHECKING:
    from smbus2 import i2c_msg


_log = logging.getLogger(__name__)


class I2CBus(SMBusABC):
    def __init__(self, bus: Union[str, int], force: bool = False) -> None:
        self._bus = bus
        self._smbus = SMBus2(bus, force)
        self.emitter = EventEmitter()
        _log.debug("SMBus initialized on bus %s with force=%s", bus, force)

    def open(self, bus: Union[int, str]) -> None:
        _log.debug("Opening SMBus on bus %s", bus)
        if hasattr(self._smbus, "open"):
            self._smbus.open(bus)
        else:
            _log.warning("Underlying SMBus instance does not support 'open'.")

    def close(self) -> None:
        _log.debug("Closing SMBus on bus %s", self._bus)
        try:
            self._smbus.close()
        except Exception as err:
            _log.error("Error closing SMBus: %s", err)
        finally:
            self.emitter.emit("close", self)
            self.emitter.off("close")

    @RETRY_DECORATOR
    def enable_pec(self, enable: bool = False) -> None:
        _log.debug("Setting PEC to %s", enable)
        self._smbus.enable_pec(enable)

    @RETRY_DECORATOR
    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        _log.debug("write_quick: addr=%s, force=%s", i2c_addr, force)
        self._smbus.write_quick(i2c_addr, force)

    @RETRY_DECORATOR
    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        _log.debug("read_byte: addr=%s, force=%s", i2c_addr, force)
        result = self._smbus.read_byte(i2c_addr, force)
        _log.debug("read_byte result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        _log.debug("write_byte: addr=%s, value=%s, force=%s", i2c_addr, value, force)
        self._smbus.write_byte(i2c_addr, value, force)

    @RETRY_DECORATOR
    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
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
    ):
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
        _log.debug("Exiting I2CBus context manager")
        self._smbus.__exit__(exc_type, exc_val, exc_tb)
