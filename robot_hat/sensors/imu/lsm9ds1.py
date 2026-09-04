"""Six-axis LSM9DS1 driver, including the Raspberry Pi Sense HAT IMU."""

import time
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.lsm9ds1 import LSM9DS1Config
from robot_hat.data_types.imu import IMUSample, RawIMUSample, RawVector3
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.interfaces.imu_abc import IMUABC
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x6A

_REG_WHO_AM_I: Final = 0x0F
_REG_CTRL_REG1_G: Final = 0x10
_REG_CTRL_REG3_G: Final = 0x12
_REG_OUT_X_L_G: Final = 0x18
_REG_CTRL_REG4: Final = 0x1E
_REG_CTRL_REG5_XL: Final = 0x1F
_REG_CTRL_REG6_XL: Final = 0x20
_REG_CTRL_REG7_XL: Final = 0x21
_REG_CTRL_REG8: Final = 0x22
_REG_OUT_X_L_XL: Final = 0x28

_WHO_AM_I_VALUE: Final = 0x68
_CTRL_REG8_BLOCK_DATA_UPDATE: Final = 0x40
_CTRL_REG8_AUTO_INCREMENT: Final = 0x04
_CTRL_REG8_SOFTWARE_RESET: Final = 0x01
_ENABLE_ALL_AXES: Final = 0x38


class LSM9DS1(IMUABC):
    """Read the LSM9DS1 accelerometer/gyroscope directly over I²C.

    Raspberry Pi Sense HAT v1 and v2 boards wire this function at address
    ``0x6a`` on bus 1. The separate magnetometer function at ``0x1c`` is not
    part of the six-axis :class:`IMUABC` contract.

    Samples use the native sensor X/Y/Z axes and signs from the ST datasheet.
    No RTIMULib axis remapping, bias learning, calibration, or sensor fusion is
    applied. Applications should configure their measured mounting transform.

    Passing a bus number creates an owned :class:`I2CBus`. Passing an existing
    :class:`SMBusABC` injects a shared bus which this driver never closes.
    """

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        bus: BusType = 1,
        config: LSM9DS1Config | None = None,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        _validate_address(address)
        self._address = address
        self.config = config if config is not None else LSM9DS1Config()
        self._monotonic_ns = monotonic_ns
        self._sleep = sleep
        self._lock = RLock()
        self._closed = False
        self._initialized = False

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
        """Validate, reset, and configure both inertial sensing functions."""

        with self._lock:
            self._ensure_open()
            if self._initialized:
                return
            try:
                self._validate_device_identity()
                self._write_byte(_REG_CTRL_REG8, _CTRL_REG8_SOFTWARE_RESET)
                self._sleep(0.1)
                self._validate_device_identity()
                self._write_byte(
                    _REG_CTRL_REG8,
                    _CTRL_REG8_BLOCK_DATA_UPDATE | _CTRL_REG8_AUTO_INCREMENT,
                )
                self._write_byte(
                    _REG_CTRL_REG1_G, self.config.gyroscope_control_register
                )
                self._write_byte(_REG_CTRL_REG3_G, 0x00)
                self._write_byte(_REG_CTRL_REG4, _ENABLE_ALL_AXES)
                self._write_byte(_REG_CTRL_REG5_XL, _ENABLE_ALL_AXES)
                self._write_byte(
                    _REG_CTRL_REG6_XL, self.config.accelerometer_control_register
                )
                self._write_byte(_REG_CTRL_REG7_XL, 0x00)
            except IMUInitializationError:
                raise
            except (OSError, TimeoutError) as error:
                raise IMUInitializationError(
                    f"failed to initialize LSM9DS1 at 0x{self._address:02X}"
                ) from error
            self._initialized = True

    def read_raw_sample(self) -> RawIMUSample:
        """Read unscaled, signed accelerometer and gyroscope counts."""

        with self._lock:
            self._ensure_ready()
            gyroscope_data = self._read_block(_REG_OUT_X_L_G, 6)
            accelerometer_data = self._read_block(_REG_OUT_X_L_XL, 6)
            return RawIMUSample(
                accelerometer_counts=_decode_vector(accelerometer_data),
                gyroscope_counts=_decode_vector(gyroscope_data),
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def read_sample(self) -> IMUSample:
        """Read one native-axis sample converted to m/s² and rad/s."""

        raw = self.read_raw_sample()
        acceleration_scale = self.config.accelerometer_mps2_per_lsb
        gyroscope_scale = self.config.gyroscope_radps_per_lsb
        return IMUSample(
            acceleration_mps2=_scale_vector(
                raw.accelerometer_counts, acceleration_scale
            ),
            angular_velocity_radps=_scale_vector(raw.gyroscope_counts, gyroscope_scale),
            timestamp_monotonic_ns=raw.timestamp_monotonic_ns,
        )

    def close(self) -> None:
        """Close only an I²C bus created by this driver."""

        with self._lock:
            if self._closed:
                return
            self._initialized = False
            self._closed = True
            if self._own_bus:
                self._bus.close()

    def __enter__(self) -> "LSM9DS1":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _validate_device_identity(self) -> None:
        identity = self._read_byte(_REG_WHO_AM_I)
        if identity != _WHO_AM_I_VALUE:
            raise IMUInitializationError(
                "LSM9DS1 WHO_AM_I mismatch: "
                f"expected 0x{_WHO_AM_I_VALUE:02X}, got 0x{identity:02X}"
            )

    def _read_byte(self, register: int) -> int:
        self._ensure_open()
        return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_block(self, register: int, length: int) -> Sequence[int]:
        data = self._bus.read_i2c_block_data(self._address, register, length)
        if len(data) != length:
            raise IMUReadError(
                f"LSM9DS1 register 0x{register:02X} returned "
                f"{len(data)} of {length} bytes"
            )
        return data

    def _write_byte(self, register: int, value: int) -> None:
        self._ensure_open()
        self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _ensure_open(self) -> None:
        if self._closed:
            raise IMUInitializationError("LSM9DS1 is closed")

    def _ensure_ready(self) -> None:
        if self._closed:
            raise IMUReadError("LSM9DS1 is closed")
        if not self._initialized:
            raise IMUReadError("call initialize() before sampling LSM9DS1")


def _decode_vector(data: Sequence[int]) -> RawVector3:
    return (
        _decode_i16(data[0], data[1]),
        _decode_i16(data[2], data[3]),
        _decode_i16(data[4], data[5]),
    )


def _decode_i16(lsb: int, msb: int) -> int:
    value = ((msb & 0xFF) << 8) | (lsb & 0xFF)
    return value - 0x10000 if value & 0x8000 else value


def _scale_vector(value: RawVector3, scale: float) -> tuple[float, float, float]:
    return (value[0] * scale, value[1] * scale, value[2] * scale)


def _validate_address(address: int) -> None:
    if isinstance(address, bool) or not isinstance(address, int):
        raise TypeError("address must be an integer")
    if address not in (0x6A, 0x6B):
        raise ValueError("LSM9DS1 accelerometer/gyroscope address must be 0x6A or 0x6B")


__all__ = ["DEFAULT_ADDRESS", "LSM9DS1"]
