"""LPS25H/LPS25HB pressure and temperature driver."""

import time
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.lps25h import LPS25HConfig
from robot_hat.data_types.environment import EnvironmentalSample
from robot_hat.exceptions import (
    EnvironmentalSensorInitializationError,
    EnvironmentalSensorReadError,
)
from robot_hat.interfaces.environmental_sensor_abc import EnvironmentalSensorABC
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x5C

_REG_WHO_AM_I: Final = 0x0F
_REG_RES_CONF: Final = 0x10
_REG_CTRL_REG1: Final = 0x20
_REG_CTRL_REG2: Final = 0x21
_REG_PRESS_OUT_XL: Final = 0x28
_AUTO_INCREMENT: Final = 0x80
_WHO_AM_I_VALUE: Final = 0xBD
_SOFTWARE_RESET: Final = 0x04
_HIGH_RESOLUTION: Final = 0x05


class LPS25H(EnvironmentalSensorABC):
    """Read pressure and temperature from LPS25H or LPS25HB over I²C.

    The Sense HAT v1 uses LPS25H while v2 uses LPS25HB. The registers used by
    this driver, identity value, and conversion formulae are shared by both.
    """

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        bus: BusType = 1,
        config: LPS25HConfig | None = None,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if address not in (0x5C, 0x5D):
            raise ValueError("LPS25H/LPS25HB I2C address must be 0x5C or 0x5D")
        self._address = address
        self.config = config if config is not None else LPS25HConfig()
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
        with self._lock:
            self._ensure_open()
            if self._initialized:
                return
            try:
                self._validate_identity()
                self._write_byte(_REG_CTRL_REG2, _SOFTWARE_RESET)
                self._sleep(0.01)
                self._validate_identity()
                self._write_byte(_REG_RES_CONF, _HIGH_RESOLUTION)
                self._write_byte(_REG_CTRL_REG1, self.config.control_register)
            except EnvironmentalSensorInitializationError:
                raise
            except (OSError, TimeoutError) as error:
                raise EnvironmentalSensorInitializationError(
                    f"failed to initialize LPS25H at 0x{self._address:02X}"
                ) from error
            self._initialized = True

    def read_sample(self) -> EnvironmentalSample:
        with self._lock:
            self._ensure_ready()
            try:
                data = self._read_block(_REG_PRESS_OUT_XL | _AUTO_INCREMENT, 5)
            except EnvironmentalSensorReadError:
                raise
            except (OSError, TimeoutError) as error:
                raise EnvironmentalSensorReadError(
                    f"failed to read LPS25H at 0x{self._address:02X}"
                ) from error
            pressure_counts = data[0] | data[1] << 8 | data[2] << 16
            temperature_counts = _decode_i16(data[3], data[4])
            return EnvironmentalSample(
                pressure_pa=pressure_counts * 100.0 / 4096.0,
                temperature_c=42.5 + temperature_counts / 480.0,
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            if self._own_bus:
                self._bus.close()

    def _validate_identity(self) -> None:
        identity = self._read_byte(_REG_WHO_AM_I)
        if identity != _WHO_AM_I_VALUE:
            raise EnvironmentalSensorInitializationError(
                "LPS25H WHO_AM_I mismatch: "
                f"expected 0x{_WHO_AM_I_VALUE:02X}, got 0x{identity:02X}"
            )

    def _read_byte(self, register: int) -> int:
        return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_block(self, register: int, length: int) -> Sequence[int]:
        data = self._bus.read_i2c_block_data(self._address, register, length)
        if len(data) != length:
            raise EnvironmentalSensorReadError(
                f"LPS25H register 0x{register:02X} returned {len(data)} of {length} bytes"
            )
        return data

    def _write_byte(self, register: int, value: int) -> None:
        self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _ensure_open(self) -> None:
        if self._closed:
            raise EnvironmentalSensorInitializationError("LPS25H is closed")

    def _ensure_ready(self) -> None:
        if self._closed:
            raise EnvironmentalSensorReadError("LPS25H is closed")
        if not self._initialized:
            raise EnvironmentalSensorReadError(
                "call initialize() before sampling LPS25H"
            )


def _decode_i16(lsb: int, msb: int) -> int:
    value = ((msb & 0xFF) << 8) | (lsb & 0xFF)
    return value - 0x10000 if value & 0x8000 else value


__all__ = ["DEFAULT_ADDRESS", "LPS25H"]
