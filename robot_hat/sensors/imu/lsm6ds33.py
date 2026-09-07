"""Six-axis LSM6DS33 accelerometer and gyroscope driver."""

import time
from threading import RLock
from typing import Callable, Final, Sequence

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.lsm6ds33 import LSM6DS33Config
from robot_hat.data_types.imu import IMUSample, RawIMUSample, RawVector3
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.interfaces.imu_abc import IMUABC
from robot_hat.interfaces.smbus_abc import SMBusABC


DEFAULT_ADDRESS: Final = 0x6B

_REG_WHO_AM_I: Final = 0x0F
_REG_CTRL1_XL: Final = 0x10
_REG_CTRL2_G: Final = 0x11
_REG_CTRL3_C: Final = 0x12
_REG_OUTX_L_G: Final = 0x22

_WHO_AM_I_VALUE: Final = 0x69
_CTRL3_C_BLOCK_DATA_UPDATE: Final = 0x40
_CTRL3_C_AUTO_INCREMENT: Final = 0x04
_CTRL3_C_SOFTWARE_RESET: Final = 0x01


class LSM6DS33(IMUABC):
    """Read an LSM6DS33 accelerometer/gyroscope directly over I²C.

    The LSM6DS33 is the six-axis inertial component on Pololu's MiniIMU-9 v5
    and AltIMU-10 v5, and is also available on standalone carrier boards. The
    separate LIS3MDL magnetometer is intentionally exposed by its own driver.

    Samples use the native sensor X/Y/Z axes and signs from the ST datasheet.
    No mounting transform, calibration, bias learning, or sensor fusion is
    applied. Passing a bus number creates an owned :class:`I2CBus`; passing an
    existing :class:`SMBusABC` injects a shared bus which this driver does not
    close.
    """

    def __init__(
        self,
        address: int = DEFAULT_ADDRESS,
        bus: BusType = 1,
        config: LSM6DS33Config | None = None,
        *,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        _validate_address(address)
        self._address = address
        self.config = config if config is not None else LSM6DS33Config()
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
                self._write_byte(_REG_CTRL3_C, _CTRL3_C_SOFTWARE_RESET)
                self._sleep(0.1)
                self._validate_device_identity()
                self._write_byte(
                    _REG_CTRL3_C,
                    _CTRL3_C_BLOCK_DATA_UPDATE | _CTRL3_C_AUTO_INCREMENT,
                )
                self._write_byte(
                    _REG_CTRL1_XL, self.config.accelerometer_control_register
                )
                self._write_byte(_REG_CTRL2_G, self.config.gyroscope_control_register)
            except IMUInitializationError:
                raise
            except (OSError, TimeoutError) as error:
                raise IMUInitializationError(
                    f"failed to initialize LSM6DS33 at 0x{self._address:02X}"
                ) from error
            self._initialized = True

    def read_raw_sample(self) -> RawIMUSample:
        """Read one contiguous block of signed gyro and accelerometer counts."""

        with self._lock:
            self._ensure_ready()
            try:
                data = self._read_block(_REG_OUTX_L_G, 12)
            except IMUReadError:
                raise
            except (OSError, TimeoutError) as error:
                raise IMUReadError(
                    f"failed to read LSM6DS33 at 0x{self._address:02X}"
                ) from error
            return RawIMUSample(
                accelerometer_counts=_decode_vector(data[6:12]),
                gyroscope_counts=_decode_vector(data[0:6]),
                timestamp_monotonic_ns=self._monotonic_ns(),
            )

    def read_sample(self) -> IMUSample:
        """Read one native-axis sample converted to m/s² and rad/s."""

        raw = self.read_raw_sample()
        return IMUSample(
            acceleration_mps2=_scale_vector(
                raw.accelerometer_counts, self.config.accelerometer_mps2_per_lsb
            ),
            angular_velocity_radps=_scale_vector(
                raw.gyroscope_counts, self.config.gyroscope_radps_per_lsb
            ),
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

    def __enter__(self) -> "LSM6DS33":
        self._ensure_open()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _validate_device_identity(self) -> None:
        identity = self._read_byte(_REG_WHO_AM_I)
        if identity != _WHO_AM_I_VALUE:
            raise IMUInitializationError(
                "LSM6DS33 WHO_AM_I mismatch: "
                f"expected 0x{_WHO_AM_I_VALUE:02X}, got 0x{identity:02X}"
            )

    def _read_byte(self, register: int) -> int:
        self._ensure_open()
        return self._bus.read_byte_data(self._address, register) & 0xFF

    def _read_block(self, register: int, length: int) -> Sequence[int]:
        data = self._bus.read_i2c_block_data(self._address, register, length)
        if len(data) != length:
            raise IMUReadError(
                f"LSM6DS33 register 0x{register:02X} returned "
                f"{len(data)} of {length} bytes"
            )
        return data

    def _write_byte(self, register: int, value: int) -> None:
        self._ensure_open()
        self._bus.write_byte_data(self._address, register, value & 0xFF)

    def _ensure_open(self) -> None:
        if self._closed:
            raise IMUInitializationError("LSM6DS33 is closed")

    def _ensure_ready(self) -> None:
        if self._closed:
            raise IMUReadError("LSM6DS33 is closed")
        if not self._initialized:
            raise IMUReadError("call initialize() before sampling LSM6DS33")


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
        raise ValueError("LSM6DS33 address must be 0x6A or 0x6B")


__all__ = ["DEFAULT_ADDRESS", "LSM6DS33"]
