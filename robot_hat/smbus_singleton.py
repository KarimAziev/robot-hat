import logging
import os
from typing import TYPE_CHECKING, List, Optional, Sequence, Union

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from robot_hat.singleton_meta import SingletonMeta

USE_MOCK = os.getenv("ROBOT_HAT_MOCK_SMBUS")

if USE_MOCK != "1":
    from smbus2 import SMBus as SMBus2
else:
    from .mock.smbus2 import MockSMBus as SMBus2


if TYPE_CHECKING:
    from smbus2 import i2c_msg


logger = logging.getLogger(__name__)

# Number of retry attempts for I2C communication
RETRY_ATTEMPTS = 5

# Initial wait time (in seconds) before retry
INITIAL_WAIT = 0.01  # 10ms

# Maximum wait time (in seconds) for retry
MAX_WAIT = 0.2  # 200ms

# Random jitter (in seconds) to add randomness to retry timing
JITTER = 0.05  # 50ms

RETRY_DECORATOR = retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential_jitter(initial=INITIAL_WAIT, max=MAX_WAIT, jitter=JITTER),
    retry=retry_if_exception_type((OSError, TimeoutError)),
    reraise=True,
)


class SMBus(metaclass=SingletonMeta):
    def __init__(self, bus: Union[str, int], force: bool = False) -> None:
        self._bus = bus
        self._smbus = SMBus2(bus, force)
        logger.debug("SMBus initialized on bus %s with force=%s", bus, force)

    def open(self, bus: Union[int, str]) -> None:
        logger.debug("Opening SMBus on bus %s", bus)
        if hasattr(self._smbus, "open"):
            self._smbus.open(bus)
        else:
            logger.warning("Underlying SMBus instance does not support 'open'.")

    def close(self) -> None:
        logger.debug("Closing SMBus on bus %s", self._bus)
        try:
            self._smbus.close()
        except Exception as err:
            logger.error("Error closing SMBus: %s", err)
        cls = self.__class__
        if cls in cls._instances:
            del cls._instances[cls]

    @RETRY_DECORATOR
    def enable_pec(self, enable: bool = False) -> None:
        logger.debug("Setting PEC to %s", enable)
        self._smbus.enable_pec(enable)

    @RETRY_DECORATOR
    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        logger.debug("write_quick: addr=%s, force=%s", i2c_addr, force)
        self._smbus.write_quick(i2c_addr, force)

    @RETRY_DECORATOR
    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        logger.debug("read_byte: addr=%s, force=%s", i2c_addr, force)
        result = self._smbus.read_byte(i2c_addr, force)
        logger.debug("read_byte result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug("write_byte: addr=%s, value=%s, force=%s", i2c_addr, value, force)
        self._smbus.write_byte(i2c_addr, value, force)

    @RETRY_DECORATOR
    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        logger.debug(
            "read_byte_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_byte_data(i2c_addr, register, force)
        logger.debug("read_byte_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug(
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
        logger.debug(
            "read_word_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_word_data(i2c_addr, register, force)
        logger.debug("read_word_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        logger.debug(
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
        logger.debug(
            "process_call: addr=%s, register=%s, value=%s, force=%s",
            i2c_addr,
            register,
            value,
            force,
        )
        result = self._smbus.process_call(i2c_addr, register, value, force)
        logger.debug("process_call result: %s", result)
        return result

    @RETRY_DECORATOR
    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug(
            "read_block_data: addr=%s, register=%s, force=%s", i2c_addr, register, force
        )
        result = self._smbus.read_block_data(i2c_addr, register, force)
        logger.debug("read_block_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        logger.debug(
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
        logger.debug(
            "block_process_call: addr=%s, register=%s, data=%s, force=%s",
            i2c_addr,
            register,
            data,
            force,
        )
        result = self._smbus.block_process_call(i2c_addr, register, data, force)
        logger.debug("block_process_call result: %s", result)
        return result

    @RETRY_DECORATOR
    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        logger.debug(
            "read_i2c_block_data: addr=%s, register=%s, length=%s, force=%s",
            i2c_addr,
            register,
            length,
            force,
        )
        result = self._smbus.read_i2c_block_data(i2c_addr, register, length, force)
        logger.debug("read_i2c_block_data result: %s", result)
        return result

    @RETRY_DECORATOR
    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        logger.debug(
            "write_i2c_block_data: addr=%s, register=%s, data=%s, force=%s",
            i2c_addr,
            register,
            data,
            force,
        )
        self._smbus.write_i2c_block_data(i2c_addr, register, data, force)

    @RETRY_DECORATOR
    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        logger.debug("i2c_rdwr: messages=%s", i2c_msgs)
        self._smbus.i2c_rdwr(*i2c_msgs)
