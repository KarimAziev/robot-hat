from dataclasses import dataclass
from typing import Literal, Optional, Union


UARTByteSize = Literal[5, 6, 7, 8]
UARTParity = Literal["N", "E", "O", "M", "S"]
UARTStopBits = Union[Literal[1, 2], float]


@dataclass(frozen=True)
class UARTConfig:
    """Configuration for a UART or USB-to-UART serial port."""

    port: str
    baudrate: int
    timeout: Optional[float] = 1.0
    write_timeout: Optional[float] = 1.0
    bytesize: UARTByteSize = 8
    parity: UARTParity = "N"
    stopbits: UARTStopBits = 1

    def __post_init__(self) -> None:
        if not self.port:
            raise ValueError("port must not be empty")
        if self.baudrate <= 0:
            raise ValueError("baudrate must be greater than zero")
        if self.timeout is not None and self.timeout < 0:
            raise ValueError("timeout must be non-negative or None")
        if self.write_timeout is not None and self.write_timeout < 0:
            raise ValueError("write_timeout must be non-negative or None")
        if self.bytesize not in (5, 6, 7, 8):
            raise ValueError("bytesize must be one of 5, 6, 7, or 8")
        if self.parity not in ("N", "E", "O", "M", "S"):
            raise ValueError("parity must be one of N, E, O, M, or S")
        if self.stopbits not in (1, 1.5, 2):
            raise ValueError("stopbits must be one of 1, 1.5, or 2")


@dataclass(frozen=True)
class USBUARTSelector:
    """Criteria used to select one USB-to-UART adapter."""

    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None


@dataclass(frozen=True)
class USBUARTDevice:
    """Metadata for a serial port reported by the operating system."""

    port: str
    description: str
    hardware_id: str
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial_number: Optional[str] = None
    manufacturer: Optional[str] = None
    product: Optional[str] = None
    location: Optional[str] = None
