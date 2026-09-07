"""LIS3MDL three-axis magnetometer driver."""

import time
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.lis3mdl import LIS3MDLConfig
from robot_hat.data_types.magnetometer import (
    MagnetometerSample,
    RawMagneticFieldVector,
    RawMagnetometerSample,
)
from robot_hat.exceptions import (
    MagnetometerInitializationError,
    MagnetometerReadError,
)
from robot_hat.interfaces.magnetometer_abc import MagnetometerABC
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x1E

_REG_WHO_AM_I: Final = 0x0F
_REG_CTRL_REG1: Final = 0x20
_REG_CTRL_REG2: Final = 0x21
_REG_CTRL_REG3: Final = 0x22
_REG_CTRL_REG4: Final = 0x23
_REG_CTRL_REG5: Final = 0x24
_REG_OUT_X_L: Final = 0x28

_AUTO_INCREMENT: Final = 0x80
_WHO_AM_I_VALUE: Final = 0x3D
_SOFTWARE_RESET: Final = 0x04
_BLOCK_DATA_UPDATE: Final = 0x40


class LIS3MDL(MagnetometerABC):
    """Read an independently addressed LIS3MDL directly over I²C.

    This is the magnetic component used by Pololu's MiniIMU-9 v5 and
    AltIMU-10 v5. Samples use the native sensor axes and do not include
    hard-iron, soft-iron, mounting, or magnetic-declination corrections.
    """

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        bus: BusType = 1,
        config: LIS3MDLConfig | None = None,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        _validate_address(address)
        self._address = address
        self.config = config if config is not None else LIS3MDLConfig()
        self._monotonic_ns = monotonic_ns
        self._sleep = sleep
        self._initialized = False
        self._closed = False
        self._lock = RLock()

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

    def initialize(self) -> None:
        """Validate, reset, and configure continuous magnetic sampling."""

        with self._lock:
            self._ensure_open()
            if self._initialized:
                return
            try:
                self._validate_device_identity()
                self._write_byte(_REG_CTRL_REG2, _SOFTWARE_RESET)
                self._sleep(0.01)
                self._validate_device_identity()
                self._write_byte(_REG_CTRL_REG1, self.config.control_register_1)
                self._write_byte(_REG_CTRL_REG2, self.config.control_register_2)
                self._write_byte(_REG_CTRL_REG3, 0x00)
                self._write_byte(_REG_CTRL_REG4, self.config.control_register_4)
                self._write_byte(_REG_CTRL_REG5, _BLOCK_DATA_UPDATE)
            except MagnetometerInitializationError:
                raise
            except (OSError, TimeoutError) as error:
                raise MagnetometerInitializationError(
                    f"failed to initialize LIS3MDL at 0x{self._address:02X}"
                ) from error
            self._initialized = True

    def read_raw_sample(self) -> RawMagnetometerSample:
        """Read unscaled, signed magnetic-field counts."""

        with self._lock:
            self._ensure_ready()
            try:
                data = self._read_block(_REG_OUT_X_L | _AUTO_INCREMENT, 6)
            except MagnetometerReadError:
                raise
            except (OSError, TimeoutError) as error:
                raise MagnetometerReadError(
                    f"failed to read LIS3MDL at 0x{self._address:02X}"
                ) from error
            return RawMagnetometerSample(
                magnetic_field_counts=_decode_vector(data),
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def read_sample(self) -> MagnetometerSample:
        """Read one native-axis magnetic-field sample in teslas."""

        raw = self.read_raw_sample()
        scale = self.config.tesla_per_lsb
        counts = raw.magnetic_field_counts
        return MagnetometerSample(
            magnetic_field_t=(
                counts[0] * scale,
                counts[1] * scale,
                counts[2] * scale,
            ),
            timestamp_monotonic_ns=raw.timestamp_monotonic_ns,
        )

    def close(self) -> None:
        """Close only an I²C bus created by this driver."""

        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            if self._own_bus:
                self._bus.close()

    def __enter__(self) -> "LIS3MDL":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _validate_device_identity(self) -> None:
        identity = self._read_byte(_REG_WHO_AM_I)
        if identity != _WHO_AM_I_VALUE:
            raise MagnetometerInitializationError(
                "LIS3MDL WHO_AM_I mismatch: "
                f"expected 0x{_WHO_AM_I_VALUE:02X}, got 0x{identity:02X}"
            )

    def _read_byte(self, register: int) -> int:
        self._ensure_open()
        return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_block(self, register: int, length: int) -> Sequence[int]:
        data = self._bus.read_i2c_block_data(self._address, register, length)
        if len(data) != length:
            raise MagnetometerReadError(
                f"LIS3MDL register 0x{register:02X} returned "
                f"{len(data)} of {length} bytes"
            )
        return data

    def _write_byte(self, register: int, value: int) -> None:
        self._ensure_open()
        self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _ensure_open(self) -> None:
        if self._closed:
            raise MagnetometerInitializationError("LIS3MDL is closed")

    def _ensure_ready(self) -> None:
        if self._closed:
            raise MagnetometerReadError("LIS3MDL is closed")
        if not self._initialized:
            raise MagnetometerReadError("call initialize() before sampling LIS3MDL")


def _decode_vector(data: Sequence[int]) -> RawMagneticFieldVector:
    return (
        _decode_i16(data[0], data[1]),
        _decode_i16(data[2], data[3]),
        _decode_i16(data[4], data[5]),
    )


def _decode_i16(lsb: int, msb: int) -> int:
    value = ((msb & 0xFF) << 8) | (lsb & 0xFF)
    return value - 0x10000 if value & 0x8000 else value


def _validate_address(address: int) -> None:
    if isinstance(address, bool) or not isinstance(address, int):
        raise TypeError("address must be an integer")
    if address not in (0x1C, 0x1E):
        raise ValueError("LIS3MDL address must be 0x1C or 0x1E")


__all__ = ["DEFAULT_ADDRESS", "LIS3MDL"]
