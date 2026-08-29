"""Deterministic SPI test doubles, including an AS5048A protocol emulator."""

from collections import deque
from collections.abc import Iterable, Sequence
from threading import RLock
from typing import Final

from robot_hat.interfaces.spi_abc import SPIABC


_AS5048A_REGISTER_NOP: Final = 0x0000
_AS5048A_REGISTER_CLEAR_ERROR: Final = 0x0001
_AS5048A_REGISTER_DIAGNOSTICS_AGC: Final = 0x3FFD
_AS5048A_REGISTER_MAGNITUDE: Final = 0x3FFE
_AS5048A_REGISTER_ANGLE: Final = 0x3FFF
_AS5048A_READ_FLAG: Final = 0x4000
_AS5048A_DATA_MASK: Final = 0x3FFF
_AS5048A_FULL_SCALE_COUNTS: Final = 16_384


class MockSPI(SPIABC):
    """Record transfers and return deterministic queued or zero responses.

    Zero-argument construction returns a same-length all-zero response. Tests
    can queue exact responses, including deliberately malformed response
    lengths for protocol error coverage.
    """

    def __init__(self, responses: Iterable[Sequence[int]] = ()) -> None:
        self._responses = deque(_validate_bytes(response) for response in responses)
        self._transfers: list[tuple[int, ...]] = []
        self._lock = RLock()
        self._closed = False

    @property
    def transfers(self) -> tuple[tuple[int, ...], ...]:
        """Return an immutable snapshot of all transmitted byte sequences."""
        with self._lock:
            return tuple(self._transfers)

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def queue_response(self, response: Sequence[int]) -> None:
        """Append a response for the next transfer."""
        with self._lock:
            self._ensure_open()
            self._responses.append(_validate_bytes(response))

    def transfer(self, data: Sequence[int]) -> list[int]:
        payload = _validate_bytes(data, allow_empty=False)
        with self._lock:
            self._ensure_open()
            self._transfers.append(tuple(payload))
            if self._responses:
                return list(self._responses.popleft())
            return [0] * len(payload)

    def close(self) -> None:
        with self._lock:
            self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("MockSPI is closed")


class MockAS5048ASPI(SPIABC):
    """Protocol-aware AS5048A SPI emulator for tests and local development.

    The emulator models the sensor's one-command pipeline, command and response
    parity, read-only registers, transient error flags, angle progression, and
    magnetic diagnostics. It performs no GPIO or Linux SPI access.
    """

    def __init__(
        self,
        *,
        angle_counts: int = 0,
        counts_per_angle_read: int = 0,
        magnitude: int = 0x2000,
        offset_compensation_finished: bool = True,
        cordic_overflow: bool = False,
        magnet_too_strong: bool = False,
        magnet_too_weak: bool = False,
        automatic_gain_control: int = 128,
    ) -> None:
        self._angle_counts = _validate_14_bit("angle_counts", angle_counts)
        if isinstance(counts_per_angle_read, bool) or not isinstance(
            counts_per_angle_read, int
        ):
            raise TypeError("counts_per_angle_read must be an integer")
        self._counts_per_angle_read = counts_per_angle_read
        self._magnitude = _validate_14_bit("magnitude", magnitude)
        self._diagnostics = _encode_diagnostics(
            offset_compensation_finished=offset_compensation_finished,
            cordic_overflow=cordic_overflow,
            magnet_too_strong=magnet_too_strong,
            magnet_too_weak=magnet_too_weak,
            automatic_gain_control=automatic_gain_control,
        )
        self._error_flags = 0
        self._pending_response = _response_frame(0)
        self._transfers: list[tuple[int, int]] = []
        self._lock = RLock()
        self._closed = False

    @property
    def transfers(self) -> tuple[tuple[int, int], ...]:
        """Return an immutable snapshot of all two-byte command frames."""
        with self._lock:
            return tuple(self._transfers)

    @property
    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def set_angle_counts(self, value: int) -> None:
        with self._lock:
            self._ensure_open()
            self._angle_counts = _validate_14_bit("angle_counts", value)

    def advance(self, counts: int) -> None:
        """Move the emulated shaft by signed 14-bit counts."""
        if isinstance(counts, bool) or not isinstance(counts, int):
            raise TypeError("counts must be an integer")
        with self._lock:
            self._ensure_open()
            self._angle_counts = (
                self._angle_counts + counts
            ) % _AS5048A_FULL_SCALE_COUNTS

    def set_magnitude(self, value: int) -> None:
        with self._lock:
            self._ensure_open()
            self._magnitude = _validate_14_bit("magnitude", value)

    def set_diagnostics(
        self,
        *,
        offset_compensation_finished: bool = True,
        cordic_overflow: bool = False,
        magnet_too_strong: bool = False,
        magnet_too_weak: bool = False,
        automatic_gain_control: int = 128,
    ) -> None:
        with self._lock:
            self._ensure_open()
            self._diagnostics = _encode_diagnostics(
                offset_compensation_finished=offset_compensation_finished,
                cordic_overflow=cordic_overflow,
                magnet_too_strong=magnet_too_strong,
                magnet_too_weak=magnet_too_weak,
                automatic_gain_control=automatic_gain_control,
            )

    def transfer(self, data: Sequence[int]) -> list[int]:
        payload = _validate_bytes(data, allow_empty=False)
        if len(payload) != 2:
            raise ValueError("MockAS5048ASPI requires exactly two bytes per transfer")

        with self._lock:
            self._ensure_open()
            self._transfers.append((payload[0], payload[1]))
            response = self._pending_response
            command = (payload[0] << 8) | payload[1]
            self._pending_response = self._execute_command(command)
            return [(response >> 8) & 0xFF, response & 0xFF]

    def close(self) -> None:
        with self._lock:
            self._closed = True

    def _execute_command(self, command: int) -> int:
        if command.bit_count() % 2:
            self._error_flags |= 1 << 2
            return _response_frame(0, error=True)

        address = command & _AS5048A_DATA_MASK
        is_read = bool(command & _AS5048A_READ_FLAG)
        if address == _AS5048A_REGISTER_NOP and not is_read:
            return _response_frame(0)
        if not is_read:
            self._error_flags |= 1 << 1
            return _response_frame(0, error=True)
        if address == _AS5048A_REGISTER_CLEAR_ERROR:
            flags = self._error_flags
            self._error_flags = 0
            return _response_frame(flags)
        if address == _AS5048A_REGISTER_DIAGNOSTICS_AGC:
            return _response_frame(self._diagnostics)
        if address == _AS5048A_REGISTER_MAGNITUDE:
            return _response_frame(self._magnitude)
        if address == _AS5048A_REGISTER_ANGLE:
            angle = self._angle_counts
            self._angle_counts = (
                angle + self._counts_per_angle_read
            ) % _AS5048A_FULL_SCALE_COUNTS
            return _response_frame(angle)

        self._error_flags |= 1 << 1
        return _response_frame(0, error=True)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("MockAS5048ASPI is closed")


def _validate_bytes(values: Sequence[int], *, allow_empty: bool = True) -> list[int]:
    result = list(values)
    if not result and not allow_empty:
        raise ValueError("SPI transfer cannot be empty")
    for value in result:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("SPI values must be integers")
        if not 0 <= value <= 0xFF:
            raise ValueError("SPI values must be bytes")
    return result


def _validate_14_bit(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 0 <= value <= _AS5048A_DATA_MASK:
        raise ValueError(f"{name} must be in [0, {_AS5048A_DATA_MASK}]")
    return value


def _encode_diagnostics(
    *,
    offset_compensation_finished: bool,
    cordic_overflow: bool,
    magnet_too_strong: bool,
    magnet_too_weak: bool,
    automatic_gain_control: int,
) -> int:
    if isinstance(automatic_gain_control, bool) or not isinstance(
        automatic_gain_control, int
    ):
        raise TypeError("automatic_gain_control must be an integer")
    if not 0 <= automatic_gain_control <= 0xFF:
        raise ValueError("automatic_gain_control must be in [0, 255]")
    return (
        automatic_gain_control
        | (int(offset_compensation_finished) << 8)
        | (int(cordic_overflow) << 9)
        | (int(magnet_too_strong) << 10)
        | (int(magnet_too_weak) << 11)
    )


def _response_frame(value: int, *, error: bool = False) -> int:
    frame = value & _AS5048A_DATA_MASK
    if error:
        frame |= _AS5048A_READ_FLAG
    if frame.bit_count() % 2:
        frame |= 0x8000
    return frame


__all__ = ["MockAS5048ASPI", "MockSPI"]
