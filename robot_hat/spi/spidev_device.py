"""Linux spidev-backed implementation of the SPI device boundary."""

from importlib import import_module
from threading import RLock
from typing import Callable, Protocol, Sequence, cast

from robot_hat.interfaces.spi_abc import SPIABC


class _SpidevHandle(Protocol):
    mode: int
    max_speed_hz: int
    bits_per_word: int

    def open(self, bus: int, device: int) -> None: ...

    def xfer2(self, data: list[int]) -> list[int]: ...

    def close(self) -> None: ...


class SpidevDevice(SPIABC):
    """One Linux ``/dev/spidev<bus>.<device>`` endpoint.

    The optional dependency is imported only during construction, so importing
    :mod:`robot_hat` remains hardware-independent on non-Linux systems.
    """

    def __init__(
        self,
        bus: int = 0,
        device: int = 0,
        *,
        mode: int = 0,
        max_speed_hz: int = 1_000_000,
        bits_per_word: int = 8,
    ) -> None:
        _validate_non_negative_integer("bus", bus)
        _validate_non_negative_integer("device", device)
        if isinstance(mode, bool) or not isinstance(mode, int) or mode not in range(4):
            raise ValueError("mode must be one of 0, 1, 2, or 3")
        if (
            isinstance(max_speed_hz, bool)
            or not isinstance(max_speed_hz, int)
            or max_speed_hz <= 0
        ):
            raise ValueError("max_speed_hz must be a positive integer")
        if (
            isinstance(bits_per_word, bool)
            or not isinstance(bits_per_word, int)
            or bits_per_word <= 0
        ):
            raise ValueError("bits_per_word must be a positive integer")

        try:
            module = import_module("spidev")
        except ModuleNotFoundError as error:
            raise RuntimeError(
                "SPI support requires the 'spidev' package on Linux; "
                "install robot-hat[spi] or install spidev>=3.8"
            ) from error

        factory = cast(Callable[[], _SpidevHandle], getattr(module, "SpiDev"))
        handle = factory()
        try:
            handle.open(bus, device)
            handle.mode = mode
            handle.max_speed_hz = max_speed_hz
            handle.bits_per_word = bits_per_word
        except Exception:
            handle.close()
            raise

        self._handle = handle
        self._lock = RLock()
        self._closed = False

    def transfer(self, data: Sequence[int]) -> list[int]:
        payload = list(data)
        if not payload:
            raise ValueError("SPI transfer cannot be empty")
        for value in payload:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError("SPI transfer values must be integers")
            if not 0 <= value <= 0xFF:
                raise ValueError("SPI transfer values must be bytes")

        with self._lock:
            self._ensure_open()
            response = self._handle.xfer2(payload)
            if len(response) != len(payload):
                raise OSError(
                    f"SPI transfer returned {len(response)} bytes; "
                    f"expected {len(payload)}"
                )
            return [value & 0xFF for value in response]

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._handle.close()

    def __enter__(self) -> "SpidevDevice":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("SpidevDevice is closed")


def _validate_non_negative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


__all__ = ["SpidevDevice"]
