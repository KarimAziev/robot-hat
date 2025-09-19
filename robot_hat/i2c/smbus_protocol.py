from __future__ import annotations

"""
SMBus / I²C protocol interface.

This module defines `SMBusProtocol`, a structural interface (typing.Protocol)
that specifies the methods and attributes expected for SMBus/I²C communication
implementations used by robot_hat. Concrete implementations need not inherit
from this Protocol; they only need to implement the same attributes/methods.
"""
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    List,
    Optional,
    Protocol,
    Sequence,
    Type,
    Union,
    runtime_checkable,
)

if TYPE_CHECKING:
    from smbus2 import I2cFunc, i2c_msg


@runtime_checkable
class SMBusProtocol(Protocol):
    """
    Structural SMBus / I²C interface.

    Attributes:
        fd: File descriptor or handle for the open bus device, if applicable.
        funcs: Bitfield of supported I²C functionality flags (smbus2.I2cFunc).
        address: Current I²C slave address configured on the bus handle, if applicable.
        force: Default force mode for operations that accept an optional `force`.
        pec: Packet Error Checking (PEC) enable state (backend-dependent).
    """

    fd: Optional[int]
    funcs: "I2cFunc"
    address: Optional[int]
    force: bool
    pec: int

    def __init__(
        self, bus: Union[None, int, str] = None, force: bool = False
    ) -> None: ...
    def __enter__(self) -> "SMBusProtocol": ...
    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...

    def open(self, bus: Union[int, str]) -> None: ...
    def close(self) -> None: ...
    def enable_pec(self, enable: bool = False) -> None: ...

    def write_quick(self, i2c_addr: int, force: Optional[bool] = None) -> None: ...

    def read_byte(self, i2c_addr: int, force: Optional[bool] = None) -> int: ...
    def write_byte(
        self, i2c_addr: int, value: int, force: Optional[bool] = None
    ) -> None: ...

    def read_byte_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int: ...
    def write_byte_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None: ...

    def read_word_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> int: ...
    def write_word_data(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> None: ...

    def process_call(
        self, i2c_addr: int, register: int, value: int, force: Optional[bool] = None
    ) -> int: ...

    def read_block_data(
        self, i2c_addr: int, register: int, force: Optional[bool] = None
    ) -> List[int]: ...
    def write_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None: ...

    def block_process_call(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> List[int]: ...

    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, force: Optional[bool] = None
    ) -> List[int]: ...
    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        force: Optional[bool] = None,
    ) -> None: ...

    def i2c_rdwr(self, *i2c_msgs: "i2c_msg") -> None: ...
