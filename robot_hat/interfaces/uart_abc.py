from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional, Type

from robot_hat.data_types.uart import UARTConfig


class UARTABC(ABC):
    """Byte-stream interface shared by hardware UARTs and USB-UART adapters."""

    @property
    @abstractmethod
    def config(self) -> UARTConfig:
        pass

    @property
    @abstractmethod
    def is_open(self) -> bool:
        pass

    @abstractmethod
    def open(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def read(self, size: int = 1) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes) -> int:
        pass

    @abstractmethod
    def reset_input_buffer(self) -> None:
        pass

    @abstractmethod
    def set_dtr(self, enabled: bool) -> None:
        pass

    def __enter__(self) -> "UARTABC":
        self.open()
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        self.close()
