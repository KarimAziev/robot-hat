"""Low-level SPI driver for the ams OSRAM AS5048A."""

from dataclasses import dataclass
from threading import RLock
from typing import Final, Protocol

from robot_hat.interfaces.spi_abc import SPIABC

FULL_SCALE_COUNTS: Final = 16_384
DEFAULT_SPI_BUS: Final = 0
DEFAULT_SPI_DEVICE: Final = 0
DEFAULT_SPI_SPEED_HZ: Final = 1_000_000
MAX_SPI_SPEED_HZ: Final = 10_000_000

_REGISTER_NOP: Final = 0x0000
_REGISTER_CLEAR_ERROR: Final = 0x0001
_REGISTER_DIAGNOSTICS_AGC: Final = 0x3FFD
_REGISTER_MAGNITUDE: Final = 0x3FFE
_REGISTER_ANGLE: Final = 0x3FFF

_READ_FLAG: Final = 0x4000
_ERROR_FLAG: Final = 0x4000
_PARITY_FLAG: Final = 0x8000
_DATA_MASK: Final = 0x3FFF


@dataclass(frozen=True)
class AS5048AErrorFlags:
    """Errors cleared from the AS5048A error register."""

    framing_error: bool
    invalid_command: bool
    parity_error: bool
    raw: int


@dataclass(frozen=True)
class AS5048ADiagnostics:
    """Decoded diagnostic and automatic-gain-control register."""

    offset_compensation_finished: bool
    cordic_overflow: bool
    magnet_too_strong: bool
    magnet_too_weak: bool
    automatic_gain_control: int
    raw: int

    @property
    def magnet_detected(self) -> bool:
        """Whether conversion completed without a CORDIC range failure."""
        return self.offset_compensation_finished and not self.cordic_overflow

    @property
    def data_valid(self) -> bool:
        """Whether angle and magnitude values are currently trustworthy."""
        return (
            self.magnet_detected
            and not self.magnet_too_strong
            and not self.magnet_too_weak
        )


class AS5048AError(OSError):
    """Base class for AS5048A communication failures."""


class AS5048AParityError(AS5048AError):
    """The sensor response did not contain valid even parity."""


class AS5048AProtocolError(AS5048AError):
    """The sensor reported an SPI framing, command, or command-parity error."""

    def __init__(self, flags: AS5048AErrorFlags) -> None:
        self.flags = flags
        details: list[str] = []
        if flags.framing_error:
            details.append("framing")
        if flags.invalid_command:
            details.append("invalid command")
        if flags.parity_error:
            details.append("command parity")
        description = ", ".join(details) if details else "unspecified"
        super().__init__(f"AS5048A SPI error: {description}")


class AS5048ASensor(Protocol):
    """Injectable read-only AS5048A sensor contract used by high-level wrappers."""

    def read_raw_angle(self) -> int: ...

    def read_angle_degrees(self) -> float: ...

    def read_diagnostics(self) -> AS5048ADiagnostics: ...

    def close(self) -> None: ...


class AS5048A:
    """Read an AS5048A using parity-checked, pipelined SPI transactions.

    With no injected device, this object opens ``/dev/spidev<bus>.<device>`` in
    SPI mode 1 at ``max_speed_hz`` and owns that handle. An injected
    :class:`SPIABC` must already use mode 1 and no more than 10 MHz; it remains
    caller-owned and is never closed here.

    This normal-operation driver intentionally does not expose OTP programming.
    """

    def __init__(
        self,
        spi: SPIABC | None = None,
        *,
        bus: int = DEFAULT_SPI_BUS,
        device: int = DEFAULT_SPI_DEVICE,
        max_speed_hz: int = DEFAULT_SPI_SPEED_HZ,
    ) -> None:
        _validate_non_negative_integer("bus", bus)
        _validate_non_negative_integer("device", device)
        if (
            isinstance(max_speed_hz, bool)
            or not isinstance(max_speed_hz, int)
            or not 0 < max_speed_hz <= MAX_SPI_SPEED_HZ
        ):
            raise ValueError(
                f"max_speed_hz must be an integer in [1, {MAX_SPI_SPEED_HZ}]"
            )

        if spi is None:
            import os

            if os.getenv("ROBOT_HAT_MOCK_SPI") == "1":
                from robot_hat.mock.spi import MockAS5048ASPI

                self._spi = MockAS5048ASPI()
            else:
                from robot_hat.spi.spidev_device import SpidevDevice

                self._spi = SpidevDevice(
                    bus=bus,
                    device=device,
                    mode=1,
                    max_speed_hz=max_speed_hz,
                    bits_per_word=8,
                )
            self._owns_spi = True
        else:
            self._spi = spi
            self._owns_spi = False

        self._lock = RLock()
        self._closed = False

    @property
    def spi(self) -> SPIABC:
        return self._spi

    @property
    def owns_spi(self) -> bool:
        return self._owns_spi

    def read_raw_angle(self) -> int:
        """Return the zero-corrected absolute angle as a 14-bit count."""
        return self.read_register(_REGISTER_ANGLE)

    def read_angle_degrees(self) -> float:
        """Return the absolute angle in the interval ``[0, 360)``."""
        return self.read_raw_angle() * 360.0 / FULL_SCALE_COUNTS

    def read_diagnostics(self) -> AS5048ADiagnostics:
        raw = self.read_register(_REGISTER_DIAGNOSTICS_AGC)
        return AS5048ADiagnostics(
            offset_compensation_finished=bool(raw & (1 << 8)),
            cordic_overflow=bool(raw & (1 << 9)),
            magnet_too_strong=bool(raw & (1 << 10)),
            magnet_too_weak=bool(raw & (1 << 11)),
            automatic_gain_control=raw & 0xFF,
            raw=raw,
        )

    def read_magnitude(self) -> int:
        """Return the 14-bit CORDIC magnetic-field magnitude."""
        return self.read_register(_REGISTER_MAGNITUDE)

    def read_register(self, address: int) -> int:
        """Read one documented 14-bit register through the pipelined protocol."""
        _validate_register_address(address)
        with self._lock:
            self._ensure_open()
            self._transfer_frame(_with_even_parity(_READ_FLAG | address))
            response = self._transfer_frame(_with_even_parity(_REGISTER_NOP))
            self._validate_response_parity(response)
            if response & _ERROR_FLAG:
                raise AS5048AProtocolError(self._clear_error_flags_locked())
            return response & _DATA_MASK

    def clear_error_flags(self) -> AS5048AErrorFlags:
        """Read and clear the sensor's transient SPI error flags."""
        with self._lock:
            self._ensure_open()
            return self._clear_error_flags_locked()

    def close(self) -> None:
        """Close only a Linux SPI handle constructed by this driver."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._owns_spi:
                self._spi.close()

    def __enter__(self) -> "AS5048A":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _clear_error_flags_locked(self) -> AS5048AErrorFlags:
        self._transfer_frame(_with_even_parity(_READ_FLAG | _REGISTER_CLEAR_ERROR))
        response = self._transfer_frame(_with_even_parity(_REGISTER_NOP))
        self._validate_response_parity(response)
        raw = response & _DATA_MASK
        return AS5048AErrorFlags(
            framing_error=bool(raw & (1 << 0)),
            invalid_command=bool(raw & (1 << 1)),
            parity_error=bool(raw & (1 << 2)),
            raw=raw,
        )

    def _transfer_frame(self, frame: int) -> int:
        response = self._spi.transfer([(frame >> 8) & 0xFF, frame & 0xFF])
        if len(response) != 2:
            raise AS5048AError(
                f"AS5048A SPI transfer returned {len(response)} bytes; expected 2"
            )
        return ((response[0] & 0xFF) << 8) | (response[1] & 0xFF)

    @staticmethod
    def _validate_response_parity(response: int) -> None:
        if response.bit_count() % 2 != 0:
            raise AS5048AParityError(
                f"AS5048A response 0x{response:04X} has invalid even parity"
            )

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("AS5048A is closed")


def _with_even_parity(frame: int) -> int:
    frame &= ~_PARITY_FLAG
    if frame.bit_count() % 2:
        frame |= _PARITY_FLAG
    return frame


def _validate_register_address(address: int) -> None:
    if isinstance(address, bool) or not isinstance(address, int):
        raise TypeError("register address must be an integer")
    if not 0 <= address <= _DATA_MASK:
        raise ValueError("register address must be a 14-bit value")


def _validate_non_negative_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


__all__ = [
    "AS5048A",
    "AS5048ADiagnostics",
    "AS5048AError",
    "AS5048AErrorFlags",
    "AS5048AParityError",
    "AS5048AProtocolError",
    "AS5048ASensor",
    "DEFAULT_SPI_BUS",
    "DEFAULT_SPI_DEVICE",
    "DEFAULT_SPI_SPEED_HZ",
    "FULL_SCALE_COUNTS",
    "MAX_SPI_SPEED_HZ",
]
