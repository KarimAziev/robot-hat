"""Low-level Raspberry Pi/SMBus driver for the ams AS5600L."""

import time
from dataclasses import dataclass
from enum import IntEnum
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x40
FULL_SCALE_COUNTS: Final = 4096

_REG_ZMCO: Final = 0x00
_REG_MANG: Final = 0x05
_REG_CONF: Final = 0x07
_REG_STATUS: Final = 0x0B
_REG_RAW_ANGLE: Final = 0x0C
_REG_AGC: Final = 0x1A
_REG_MAGNITUDE: Final = 0x1B
_REG_I2C_ADDRESS: Final = 0x20
_REG_I2C_UPDATE: Final = 0x21
_REG_BURN: Final = 0xFF

_STATUS_MAGNET_TOO_STRONG: Final = 0x08
_STATUS_MAGNET_TOO_WEAK: Final = 0x10
_STATUS_MAGNET_DETECTED: Final = 0x20

_CONF_SLOW_FILTER_MASK: Final = 0b11 << 8
_CONF_FAST_FILTER_MASK: Final = 0b111 << 10
_CONF_VALID_MASK: Final = 0x3FFF
_BURN_SETTING: Final = 0x40
_OTP_RELOAD_SEQUENCE: Final = (0x01, 0x11, 0x10)


class AS5600LSlowFilter(IntEnum):
    """AS5600L slow-filter averaging setting."""

    X16 = 0
    X8 = 1
    X4 = 2
    X2 = 3


class AS5600LFastFilterThreshold(IntEnum):
    """AS5600L fast-filter threshold selection."""

    OFF = 0
    LSB_6 = 1
    LSB_7 = 2
    LSB_9 = 3
    LSB_18 = 4
    LSB_21 = 5
    LSB_24 = 6
    LSB_10 = 7


@dataclass(frozen=True)
class AS5600LStatus:
    """Decoded AS5600L magnet status register."""

    magnet_detected: bool
    magnet_too_weak: bool
    magnet_too_strong: bool
    raw: int


@dataclass(frozen=True)
class AS5600LAddressProgrammingResult:
    """Verified result of one permanent address programming operation."""

    old_address: int
    new_address: int
    configuration: int
    maximum_angle: int
    otp_readback_verified: bool
    power_cycle_verification_required: bool = True


@dataclass(frozen=True)
class AS5600LAddressProgrammingPlan:
    """Reviewed state that must remain unchanged before an OTP address burn."""

    current_address: int
    new_address: int
    configuration: int
    maximum_angle: int
    zero_position_burn_count: int

    @property
    def confirmation_phrase(self) -> str:
        """Return an exact phrase containing every setting burned by the command."""

        return (
            f"BURN AS5600L ADDRESS 0x{self.new_address:02X} "
            f"CONF 0x{self.configuration:04X} MANG 0x{self.maximum_angle:03X}"
        )


class AS5600L:
    """Read and configure an AS5600L without permanently burning OTP.

    Passing a bus number creates an owned :class:`I2CBus`; passing an existing
    :class:`SMBusABC` injects a shared bus which is never closed by this object.
    Permanent programming is intentionally available only through
    :class:`AS5600LAddressProgrammer`.
    """

    def __init__(self, bus: BusType = 1, address: int = DEFAULT_ADDRESS) -> None:
        _validate_address(address)
        self._address = address
        self._lock = RLock()
        self._closed = False

        if isinstance(bus, int):
            from robot_hat.i2c.i2c_bus import I2CBus

            self._bus = I2CBus(bus)
            self._own_bus = True
        else:
            self._bus = bus
            self._own_bus = False

    @property
    def address(self) -> int:
        return self._address

    @property
    def bus(self) -> SMBusABC:
        return self._bus

    @property
    def own_bus(self) -> bool:
        return self._own_bus

    def read_raw_angle(self) -> int:
        """Read the unscaled, unmodified 12-bit magnetic angle."""
        return self._read_u12(_REG_RAW_ANGLE)

    def read_angle_degrees(self) -> float:
        """Read the raw angle converted to degrees in ``[0, 360)``."""
        return self.read_raw_angle() * 360.0 / FULL_SCALE_COUNTS

    def read_status(self) -> AS5600LStatus:
        raw = self._read_byte(_REG_STATUS)
        return AS5600LStatus(
            magnet_detected=bool(raw & _STATUS_MAGNET_DETECTED),
            magnet_too_weak=bool(raw & _STATUS_MAGNET_TOO_WEAK),
            magnet_too_strong=bool(raw & _STATUS_MAGNET_TOO_STRONG),
            raw=raw,
        )

    def read_magnitude(self) -> int:
        return self._read_u12(_REG_MAGNITUDE)

    def read_gain(self) -> int:
        return self._read_byte(_REG_AGC)

    def read_configuration(self) -> int:
        """Return the 14-bit CONF register."""
        return self._read_u16(_REG_CONF) & _CONF_VALID_MASK

    def configure_filter(
        self,
        *,
        slow_filter: AS5600LSlowFilter = AS5600LSlowFilter.X16,
        fast_filter_threshold: AS5600LFastFilterThreshold = (
            AS5600LFastFilterThreshold.OFF
        ),
    ) -> None:
        """Configure digital filtering while preserving all unrelated bits."""
        with self._lock:
            configuration = self.read_configuration()
            configuration &= ~(_CONF_SLOW_FILTER_MASK | _CONF_FAST_FILTER_MASK)
            configuration |= int(slow_filter) << 8
            configuration |= int(fast_filter_threshold) << 10
            self._write_u16(_REG_CONF, configuration)

    def set_temporary_address(self, address: int) -> None:
        """Change the active I²C address until the next power-on reset."""
        _validate_address(address)
        with self._lock:
            self._write_byte(_REG_I2C_ADDRESS, address)
            self._write_byte(_REG_I2C_UPDATE, address)
            self._address = address

    def close(self) -> None:
        """Close only an I²C bus created by this driver."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            if self._own_bus:
                self._bus.close()

    def __enter__(self) -> "AS5600L":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("AS5600L is closed")

    def _read_byte(self, register: int) -> int:
        with self._lock:
            self._ensure_open()
            return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_u12(self, register: int) -> int:
        return self._read_u16(register) & 0x0FFF

    def _read_u16(self, register: int) -> int:
        with self._lock:
            self._ensure_open()
            data: Sequence[int] = self._bus.read_i2c_block_data(
                self._address, register, 2
            )
            if len(data) != 2:
                raise OSError(
                    f"AS5600L register 0x{register:02X} returned {len(data)} bytes"
                )
            return ((data[0] & 0xFF) << 8) | (data[1] & 0xFF)

    def _write_byte(self, register: int, value: int) -> None:
        with self._lock:
            self._ensure_open()
            self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _write_u16(self, register: int, value: int) -> None:
        with self._lock:
            self._ensure_open()
            self._bus.write_i2c_block_data(
                self._address,
                register,
                [(value >> 8) & 0xFF, value & 0xFF],
            )


class AS5600LAddressProgrammer:
    """Explicit, hazardous AS5600L permanent-address programming utility.

    ``BURN_SETTING`` also burns the current MANG and CONF register contents.
    This class is therefore deliberately separate from normal sensor startup.
    """

    def __init__(
        self,
        bus: BusType = 1,
        address: int = DEFAULT_ADDRESS,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._driver = AS5600L(bus=bus, address=address)
        self._sleep = sleep

    def prepare_address_programming(
        self, address: int
    ) -> AS5600LAddressProgrammingPlan:
        """Inspect and validate all live settings affected by ``BURN_SETTING``.

        The sensor must be power-cycled before preparing a plan so the readable
        configuration reflects OTP rather than an earlier volatile change. Only
        one AS5600L may be connected while programming, because immediate
        verification may need to probe both the old and new addresses.
        """

        _validate_address(address)
        current_address = self._driver._read_byte(_REG_I2C_ADDRESS) & 0x7F
        if current_address != self._driver.address:
            raise ValueError(
                "AS5600L I2CADDR does not match the active address; power-cycle "
                "the isolated sensor before preparing an OTP programming plan"
            )
        if address == current_address:
            raise ValueError("new address must differ from the current address")
        if not _otp_address_transition_is_possible(current_address, address):
            raise ValueError(
                f"OTP cannot change AS5600L address 0x{current_address:02X} "
                f"to 0x{address:02X}"
            )

        zero_position_burn_count = self._driver._read_byte(_REG_ZMCO) & 0x03
        if zero_position_burn_count != 0:
            raise ValueError(
                "BURN_SETTING is unsafe after ZPOS or MPOS was programmed; "
                f"ZMCO is {zero_position_burn_count}"
            )
        return AS5600LAddressProgrammingPlan(
            current_address=current_address,
            new_address=address,
            configuration=self._driver.read_configuration(),
            maximum_angle=self._driver._read_u12(_REG_MANG),
            zero_position_burn_count=zero_position_burn_count,
        )

    def program_address(
        self,
        plan: AS5600LAddressProgrammingPlan,
        *,
        confirmation: str,
    ) -> AS5600LAddressProgrammingResult:
        """Burn a previously reviewed plan and immediately verify OTP readback.

        A subsequent power cycle and :meth:`verify_programmed_address` call are
        still required to establish that the device starts at the new address.
        """
        if not isinstance(plan, AS5600LAddressProgrammingPlan):
            raise TypeError("plan must be an AS5600LAddressProgrammingPlan")
        if confirmation != plan.confirmation_phrase:
            raise ValueError(
                "permanent programming requires confirmation "
                f"{plan.confirmation_phrase!r}"
            )

        live_plan = self.prepare_address_programming(plan.new_address)
        if live_plan != plan:
            raise ValueError(
                "AS5600L settings changed after the programming plan was reviewed"
            )

        self._driver._write_byte(_REG_I2C_ADDRESS, plan.new_address)
        self._sleep(0.001)
        self._driver._write_byte(_REG_BURN, _BURN_SETTING)
        self._sleep(0.005)
        self._reload_otp()

        verified_address: int | None = None
        try:
            self._driver._address = plan.new_address
            verified_address = self._driver._read_byte(_REG_I2C_ADDRESS) & 0x7F
        except OSError:
            # Some parts retain the old active address until a real power-on
            # reset even after the OTP reload sequence.
            self._driver._address = plan.current_address
            verified_address = self._driver._read_byte(_REG_I2C_ADDRESS) & 0x7F
        verified_configuration = self._driver.read_configuration()
        verified_maximum_angle = self._driver._read_u12(_REG_MANG)
        verified = (
            verified_address == plan.new_address
            and verified_configuration == plan.configuration
            and verified_maximum_angle == plan.maximum_angle
        )
        if not verified:
            raise OSError(
                "AS5600L OTP verification failed; power-cycle the device and "
                "inspect its address and configuration before retrying"
            )

        return AS5600LAddressProgrammingResult(
            old_address=plan.current_address,
            new_address=plan.new_address,
            configuration=plan.configuration,
            maximum_angle=plan.maximum_angle,
            otp_readback_verified=True,
        )

    def verify_programmed_address(self, expected_address: int) -> bool:
        """Verify OTP address readback, normally after a device power cycle."""
        _validate_address(expected_address)
        programmed_address = self._driver._read_byte(_REG_I2C_ADDRESS) & 0x7F
        self._driver.read_status()
        return programmed_address == expected_address

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "AS5600LAddressProgrammer":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _reload_otp(self) -> None:
        for command in _OTP_RELOAD_SEQUENCE:
            self._driver._write_byte(_REG_BURN, command)
        self._sleep(0.005)


def _validate_address(address: int) -> None:
    if isinstance(address, bool) or not isinstance(address, int):
        raise TypeError("address must be an integer")
    if not 0x08 <= address <= 0x77:
        raise ValueError("address must be an unreserved 7-bit I2C address (0x08-0x77)")


def _otp_address_transition_is_possible(current: int, requested: int) -> bool:
    """Return whether the AS5600L one-way OTP bits can represent ``requested``."""

    lower_address_bits = 0x3F
    lower_bit_would_clear = bool((current & lower_address_bits) & ~requested)
    msb_would_return_to_one = not bool(current & 0x40) and bool(requested & 0x40)
    return not lower_bit_would_clear and not msb_would_return_to_one


__all__ = [
    "AS5600L",
    "AS5600LAddressProgrammer",
    "AS5600LAddressProgrammingPlan",
    "AS5600LAddressProgrammingResult",
    "AS5600LFastFilterThreshold",
    "AS5600LSlowFilter",
    "AS5600LStatus",
    "DEFAULT_ADDRESS",
    "FULL_SCALE_COUNTS",
]
