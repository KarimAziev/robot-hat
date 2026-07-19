import logging
from typing import TYPE_CHECKING, Optional, cast

from robot_hat.data_types.uart import UARTConfig
from robot_hat.exceptions import UARTConnectionError
from robot_hat.interfaces.uart_abc import UARTABC

if TYPE_CHECKING:
    from serial import Serial


_log = logging.getLogger(__name__)


class SerialUART(UARTABC):
    """PySerial-backed UART suitable for native and USB serial ports."""

    def __init__(self, config: UARTConfig) -> None:
        self._config = config
        self._serial: Optional["Serial"] = None

    @property
    def config(self) -> UARTConfig:
        return self._config

    @property
    def is_open(self) -> bool:
        return self._serial is not None and bool(self._serial.is_open)

    def open(self) -> None:
        if self.is_open:
            return
        try:
            import serial
        except ImportError as error:
            raise UARTConnectionError(
                "PySerial is required for UART access; install robot-hat with its "
                "declared dependencies"
            ) from error
        try:
            self._serial = serial.Serial(
                port=self._config.port,
                baudrate=self._config.baudrate,
                timeout=self._config.timeout,
                write_timeout=self._config.write_timeout,
                bytesize=self._config.bytesize,
                parity=self._config.parity,
                stopbits=self._config.stopbits,
            )
        except (OSError, serial.SerialException) as error:
            raise UARTConnectionError(
                f"Unable to open UART port {self._config.port!r} at "
                f"{self._config.baudrate} baud: {error}"
            ) from error
        _log.debug(
            "Opened UART port %s at %d baud",
            self._config.port,
            self._config.baudrate,
        )

    def close(self) -> None:
        serial_port = self._serial
        self._serial = None
        if serial_port is None:
            return
        try:
            serial_port.close()
        except Exception as error:
            raise UARTConnectionError(
                f"Unable to close UART port {self._config.port!r}: {error}"
            ) from error
        _log.debug("Closed UART port %s", self._config.port)

    def _require_serial(self) -> "Serial":
        if not self.is_open:
            raise UARTConnectionError(f"UART port {self._config.port!r} is not open")
        return cast("Serial", self._serial)

    def read(self, size: int = 1) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative")
        try:
            return bytes(self._require_serial().read(size))
        except Exception as error:
            if isinstance(error, UARTConnectionError):
                raise
            raise UARTConnectionError(
                f"Unable to read from UART port {self._config.port!r}: {error}"
            ) from error

    def write(self, data: bytes) -> int:
        try:
            written = self._require_serial().write(data)
            if written is None:
                raise UARTConnectionError(
                    f"UART port {self._config.port!r} did not report a write count"
                )
            return written
        except Exception as error:
            if isinstance(error, UARTConnectionError):
                raise
            raise UARTConnectionError(
                f"Unable to write to UART port {self._config.port!r}: {error}"
            ) from error

    def reset_input_buffer(self) -> None:
        try:
            self._require_serial().reset_input_buffer()
        except Exception as error:
            if isinstance(error, UARTConnectionError):
                raise
            raise UARTConnectionError(
                f"Unable to reset UART port {self._config.port!r}: {error}"
            ) from error

    def set_dtr(self, enabled: bool) -> None:
        try:
            self._require_serial().dtr = enabled
        except Exception as error:
            if isinstance(error, UARTConnectionError):
                raise
            raise UARTConnectionError(
                f"Unable to set DTR on UART port {self._config.port!r}: {error}"
            ) from error
