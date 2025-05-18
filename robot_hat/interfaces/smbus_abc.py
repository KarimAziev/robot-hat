from abc import ABC, abstractmethod
from types import TracebackType
from typing import TYPE_CHECKING, List, Optional, Sequence, Type, Union

if TYPE_CHECKING:
    from smbus2 import I2cFunc, i2c_msg


class SMBusABC(ABC):
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
        pass

    @abstractmethod
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        pass

    @abstractmethod
    def open(self, bus: Union[int, str]) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def enable_pec(self, enable: bool = False) -> None:
        pass

    @abstractmethod
    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None:
        pass

    @abstractmethod
    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int:
        pass

    @abstractmethod
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None:
        pass

    @abstractmethod
    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        pass

    @abstractmethod
    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        pass

    @abstractmethod
    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int:
        pass

    @abstractmethod
    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None:
        pass

    @abstractmethod
    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ):
        pass

    @abstractmethod
    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]:
        pass

    @abstractmethod
    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        pass

    @abstractmethod
    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> List[int]:
        pass

    @abstractmethod
    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]:
        pass

    @abstractmethod
    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None:
        pass

    @abstractmethod
    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None:
        pass
