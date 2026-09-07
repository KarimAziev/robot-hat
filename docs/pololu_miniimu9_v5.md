# Pololu MiniIMU-9 v5 support

The Pololu MiniIMU-9 v5 combines two independently addressed ST sensors:

| Measurement                                  | `robot_hat` driver | Default address | Address with `SA0` low |
| -------------------------------------------- | ------------------ | --------------- | ---------------------- |
| Three-axis acceleration and angular velocity | `LSM6DS33`         | `0x6b`          | `0x6a`                 |
| Three-axis magnetic field                    | `LIS3MDL`          | `0x1e`          | `0x1c`                 |

The drivers are named after their sensor ICs rather than the Pololu carrier.
They can therefore be used independently with standalone LSM6DS33 or LIS3MDL
breakouts and together on the MiniIMU-9 v5 or AltIMU-10 v5. `LSM6DS33`
implements `IMUABC`; `LIS3MDL` implements `MagnetometerABC`.

## Wiring and addresses

Connect `VIN`, `GND`, `SCL`, and `SDA`. The MiniIMU carrier accepts 2.5–5.5 V at
`VIN` and level-shifts I²C to that voltage. When bypassing the regulator, connect
a 2.5–3.3 V supply to `VDD` with `VIN` disconnected. Never drive `VDD` while
`VIN` is connected, and do not apply more than 3.6 V to `VDD`.

The board pulls `SA0` high. Driving it low changes both sensor addresses as
shown in the table. `SA0` is 3.3 V logic and is not 5 V tolerant. The carrier
does not expose the sensor chip-select pins, so only I²C—not SPI—is available on
this board.

## Shared-bus example

Use one injected bus when both sensor components are needed:

```python
from robot_hat import (
    I2CBus,
    LIS3MDL,
    LIS3MDLConfig,
    LSM6DS33,
    LSM6DS33Config,
)

bus = I2CBus(1)
imu = LSM6DS33(
    bus=bus,
    address=0x6B,
    config=LSM6DS33Config(
        accelerometer_range_g=2,
        gyroscope_range_dps=500,
        output_data_rate_hz=104,
    ),
)
magnetometer = LIS3MDL(
    bus=bus,
    address=0x1E,
    config=LIS3MDLConfig(
        magnetic_field_range_gauss=4,
        output_data_rate_hz=20.0,
        performance_mode="ultra_high",
    ),
)

try:
    imu.initialize()
    magnetometer.initialize()
    inertial_sample = imu.read_sample()
    magnetic_sample = magnetometer.read_sample()
finally:
    magnetometer.close()
    imu.close()
    bus.close()
```

An injected `SMBusABC` remains caller-owned: neither sensor closes it. When a
numeric bus ID is passed instead, that driver creates and owns its own `I2CBus`.
For a two-chip board, a shared injected bus is usually the clearer choice.

## Configuration and units

`LSM6DS33Config` supports:

- accelerometer ranges of ±2, ±4, ±8, and ±16 g;
- gyroscope ranges of ±125, ±245, ±500, ±1000, and ±2000 degrees/s;
- a shared enabled output rate of 13, 26, 52, 104, 208, 416, 833, or 1666 Hz.

`read_sample()` converts those readings to metres per second squared and radians
per second. The default is ±2 g, ±245 degrees/s, and 104 Hz. The driver enables
block-data update and register auto-increment, then reads all six axes in one
contiguous I²C transaction. `read_raw_sample()` exposes signed counts for
diagnostics and calibration.

`LIS3MDLConfig` supports magnetic ranges of ±4, ±8, ±12, and ±16 gauss, output
rates from 0.625 to 80 Hz, and low, medium, high, or ultra-high performance. Its
default is ±4 gauss, 10 Hz, and ultra-high performance, matching Pololu's
reference initialization except that block-data update is also enabled. Samples
are returned in teslas. `read_raw_sample()` exposes signed counts.

## Frames and calibration

Both drivers report the native X/Y/Z axes and signs documented by ST. The axes
of the two ICs are aligned on the MiniIMU-9 v5, but `robot_hat` does not apply a
carrier-to-robot mounting transform. The consuming application owns that rigid
transform.

The drivers apply only the datasheet scale factors. They do not estimate gyro
bias, correct accelerometer offsets, calibrate hard-iron or soft-iron magnetic
distortion, compensate local magnetic declination, or perform AHRS sensor
fusion. Perform those operations in calibration or localization code, where
their frames and assumptions are explicit.

## References

- [Pololu MiniIMU-9 v5 product documentation](https://www.pololu.com/product/2738)
- [ST LSM6DS33 datasheet](https://www.pololu.com/file/0J1087/LSM6DS33.pdf)
- [ST LIS3MDL datasheet](https://www.pololu.com/file/0J1089/LIS3MDL.pdf)
- [Pololu LSM6 Arduino library](https://github.com/pololu/lsm6-arduino)
- [Pololu LIS3MDL Arduino library](https://github.com/pololu/lis3mdl-arduino)
