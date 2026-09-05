"""HTS221 temperature and relative-humidity driver."""

import time
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.hts221 import HTS221Config
from robot_hat.data_types.environment import EnvironmentalSample
from robot_hat.exceptions import (
    EnvironmentalSensorInitializationError,
    EnvironmentalSensorReadError,
)
from robot_hat.interfaces.environmental_sensor_abc import EnvironmentalSensorABC
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x5F

_REG_WHO_AM_I: Final = 0x0F
_REG_AV_CONF: Final = 0x10
_REG_CTRL_REG1: Final = 0x20
_REG_HUMIDITY_OUT_L: Final = 0x28
_REG_H0_RH_X2: Final = 0x30
_REG_H1_RH_X2: Final = 0x31
_REG_T0_DEGC_X8: Final = 0x32
_REG_T1_DEGC_X8: Final = 0x33
_REG_T1_T0_MSB: Final = 0x35
_REG_H0_T0_OUT_L: Final = 0x36
_REG_H1_T0_OUT_L: Final = 0x3A
_REG_T0_OUT_L: Final = 0x3C
_REG_T1_OUT_L: Final = 0x3E
_AUTO_INCREMENT: Final = 0x80
_WHO_AM_I_VALUE: Final = 0xBC


@dataclass(frozen=True)
class _Calibration:
    humidity_slope: float
    humidity_intercept: float
    temperature_slope: float
    temperature_intercept: float


class HTS221(EnvironmentalSensorABC):
    """Read factory-calibrated temperature and relative humidity over I²C."""

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        bus: BusType = 1,
        config: HTS221Config | None = None,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        if address != DEFAULT_ADDRESS:
            raise ValueError("HTS221 I2C address must be 0x5F")
        self._address = address
        self.config = config if config is not None else HTS221Config()
        self._monotonic_ns = monotonic_ns
        self._calibration: _Calibration | None = None
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
                identity = self._read_byte(_REG_WHO_AM_I)
                if identity != _WHO_AM_I_VALUE:
                    raise EnvironmentalSensorInitializationError(
                        "HTS221 WHO_AM_I mismatch: "
                        f"expected 0x{_WHO_AM_I_VALUE:02X}, got 0x{identity:02X}"
                    )
                calibration = self._read_calibration()
                self._write_byte(_REG_AV_CONF, self.config.averaging_register)
                self._write_byte(_REG_CTRL_REG1, self.config.control_register)
            except EnvironmentalSensorInitializationError:
                raise
            except EnvironmentalSensorReadError as error:
                raise EnvironmentalSensorInitializationError(
                    f"failed to read HTS221 calibration at 0x{self._address:02X}"
                ) from error
            except (OSError, TimeoutError) as error:
                raise EnvironmentalSensorInitializationError(
                    f"failed to initialize HTS221 at 0x{self._address:02X}"
                ) from error
            self._calibration = calibration
            self._initialized = True

    def read_sample(self) -> EnvironmentalSample:
        with self._lock:
            calibration = self._ensure_ready()
            try:
                data = self._read_block(_REG_HUMIDITY_OUT_L | _AUTO_INCREMENT, 4)
            except EnvironmentalSensorReadError:
                raise
            except (OSError, TimeoutError) as error:
                raise EnvironmentalSensorReadError(
                    f"failed to read HTS221 at 0x{self._address:02X}"
                ) from error
            raw_humidity = _decode_i16(data[0], data[1])
            raw_temperature = _decode_i16(data[2], data[3])
            humidity = (
                raw_humidity * calibration.humidity_slope
                + calibration.humidity_intercept
            )
            temperature = (
                raw_temperature * calibration.temperature_slope
                + calibration.temperature_intercept
            )
            return EnvironmentalSample(
                temperature_c=temperature,
                relative_humidity_percent=min(100.0, max(0.0, humidity)),
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._initialized = False
            self._calibration = None
            if self._own_bus:
                self._bus.close()

    def _read_calibration(self) -> _Calibration:
        h0 = self._read_byte(_REG_H0_RH_X2) / 2.0
        h1 = self._read_byte(_REG_H1_RH_X2) / 2.0
        t0_low = self._read_byte(_REG_T0_DEGC_X8)
        t1_low = self._read_byte(_REG_T1_DEGC_X8)
        temperature_msbs = self._read_byte(_REG_T1_T0_MSB)
        t0 = (((temperature_msbs & 0x03) << 8) | t0_low) / 8.0
        t1 = ((((temperature_msbs >> 2) & 0x03) << 8) | t1_low) / 8.0
        h0_out = self._read_i16(_REG_H0_T0_OUT_L)
        h1_out = self._read_i16(_REG_H1_T0_OUT_L)
        t0_out = self._read_i16(_REG_T0_OUT_L)
        t1_out = self._read_i16(_REG_T1_OUT_L)
        if h1_out == h0_out or t1_out == t0_out:
            raise EnvironmentalSensorInitializationError(
                "HTS221 factory calibration contains coincident ADC points"
            )
        humidity_slope = (h1 - h0) / (h1_out - h0_out)
        temperature_slope = (t1 - t0) / (t1_out - t0_out)
        return _Calibration(
            humidity_slope=humidity_slope,
            humidity_intercept=h0 - humidity_slope * h0_out,
            temperature_slope=temperature_slope,
            temperature_intercept=t0 - temperature_slope * t0_out,
        )

    def _read_byte(self, register: int) -> int:
        return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_i16(self, register: int) -> int:
        data = self._read_block(register | _AUTO_INCREMENT, 2)
        return _decode_i16(data[0], data[1])

    def _read_block(self, register: int, length: int) -> Sequence[int]:
        data = self._bus.read_i2c_block_data(self._address, register, length)
        if len(data) != length:
            raise EnvironmentalSensorReadError(
                f"HTS221 register 0x{register:02X} returned {len(data)} of {length} bytes"
            )
        return data

    def _write_byte(self, register: int, value: int) -> None:
        self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _ensure_open(self) -> None:
        if self._closed:
            raise EnvironmentalSensorInitializationError("HTS221 is closed")

    def _ensure_ready(self) -> _Calibration:
        if self._closed:
            raise EnvironmentalSensorReadError("HTS221 is closed")
        if not self._initialized or self._calibration is None:
            raise EnvironmentalSensorReadError(
                "call initialize() before sampling HTS221"
            )
        return self._calibration


def _decode_i16(lsb: int, msb: int) -> int:
    value = ((msb & 0xFF) << 8) | (lsb & 0xFF)
    return value - 0x10000 if value & 0x8000 else value


__all__ = ["DEFAULT_ADDRESS", "HTS221"]
