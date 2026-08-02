from typing import List, Optional

from robot_hat.data_types.uart import UARTConfig
from robot_hat.interfaces.uart_abc import UARTABC


class MockUART(UARTABC):
    """Deterministic in-memory UART for protocol tests and applications."""

    def __init__(
        self,
        read_data: bytes = b"",
        *,
        config: Optional[UARTConfig] = None,
        max_read_size: Optional[int] = None,
    ) -> None:
        self._config = config or UARTConfig(port="mock://", baudrate=115200)
        self._read_buffer = bytearray(read_data)
        self.max_read_size = max_read_size
        self.writes: List[bytes] = []
        self.dtr = False
        self.input_reset_count = 0
        self._is_open = False

    @property
    def config(self) -> UARTConfig:
        return self._config

    @property
    def is_open(self) -> bool:
        return self._is_open

    def open(self) -> None:
        self._is_open = True

    def close(self) -> None:
        self._is_open = False

    def queue_read_data(self, data: bytes) -> None:
        self._read_buffer.extend(data)

    def read(self, size: int = 1) -> bytes:
        if not self.is_open:
            raise RuntimeError("MockUART is not open")
        if size < 0:
            raise ValueError("size must be non-negative")
        actual_size = size
        if self.max_read_size is not None:
            actual_size = min(actual_size, self.max_read_size)
        actual_size = min(actual_size, len(self._read_buffer))
        result = bytes(self._read_buffer[:actual_size])
        del self._read_buffer[:actual_size]
        return result

    def write(self, data: bytes) -> int:
        if not self.is_open:
            raise RuntimeError("MockUART is not open")
        self.writes.append(bytes(data))
        return len(data)

    def reset_input_buffer(self) -> None:
        if not self.is_open:
            raise RuntimeError("MockUART is not open")
        self.input_reset_count += 1

    def set_dtr(self, enabled: bool) -> None:
        if not self.is_open:
            raise RuntimeError("MockUART is not open")
        self.dtr = enabled
