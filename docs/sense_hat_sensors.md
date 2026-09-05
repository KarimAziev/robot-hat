# Sense HAT environmental and magnetic sensors

Sense HAT support is component-oriented. Applications can use any driver on its
own, combine the Sense HAT devices, or mix them with sensors on another board.
No `sense-hat` or RTIMULib installation is required.

## Hardware map

| Measurement | Driver | Default I²C address | Sense HAT revision |
| --- | --- | --- | --- |
| Temperature and relative humidity | `HTS221` | `0x5f` | v1 and v2 |
| Barometric pressure and temperature | `LPS25H` | `0x5c` | v1 (LPS25H), v2 (LPS25HB) |
| Three-axis magnetic field | `LSM9DS1Magnetometer` | `0x1c` | v1 and v2 |

The LPS25H and LPS25HB have the same identity value, output registers, and
conversion formulae used here. The driver name follows the original Sense HAT
part but supports both board revisions.

## Contracts and units

`EnvironmentalSensorABC` returns an immutable `EnvironmentalSample`. Each
physical sensor fills only its supported values:

- temperature in degrees Celsius;
- relative humidity as a percentage in the closed interval 0 through 100;
- absolute pressure in pascals;
- a process-local `time.monotonic_ns()` timestamp.

`MagnetometerABC` returns a native-axis `MagnetometerSample` in teslas. The
driver deliberately does not apply hard-iron offsets, soft-iron correction,
declination, board rotation, or heading calculation. Those depend on the
installation and belong in application calibration or sensor fusion.

The Sense HAT temperature sensors are physically close to the Raspberry Pi and
LED matrix. Their readings can therefore be warmer than ambient air. The two
temperature values also come from different physical devices and should remain
distinguishable instead of being silently averaged.

## Configuration and ownership

The default settings favor modest telemetry rates:

```python
from robot_hat import (
    HTS221,
    HTS221Config,
    LPS25H,
    LPS25HConfig,
    LSM9DS1Magnetometer,
    LSM9DS1MagnetometerConfig,
    SMBusManager,
)

manager = SMBusManager()
bus = manager.get_bus(1)
sensors = [
    HTS221(bus=bus, config=HTS221Config(output_data_rate_hz=1.0)),
    LPS25H(bus=bus, config=LPS25HConfig(output_data_rate_hz=1.0)),
    LSM9DS1Magnetometer(
        bus=bus,
        config=LSM9DS1MagnetometerConfig(
            magnetic_field_range_gauss=4,
            output_data_rate_hz=20.0,
            performance_mode="ultra_high",
        ),
    ),
]
try:
    for sensor in sensors:
        sensor.initialize()
        print(sensor.read_sample())
finally:
    for sensor in sensors:
        sensor.close()  # The injected shared bus remains open.
    manager.close_all()
```

Passing a numeric bus creates an I²C resource owned by that driver. Passing an
`SMBusABC` injects a caller-owned resource, so closing the sensor leaves the bus
open. `MockEnvironmentalSensor` and `MockMagnetometer` provide deterministic
hardware-free implementations with mutable samples and availability controls.

## References

- [Raspberry Pi Sense HAT documentation](https://www.raspberrypi.com/documentation/hardware/sense-hat/)
- [Sense HAT v1 schematic](https://datasheets.raspberrypi.com/sense-hat/sense-hat-schematics.pdf)
- [Sense HAT v2 schematic](https://datasheets.raspberrypi.com/sense-hat/sense-hat-v2-schematics.pdf)
- [ST HTS221 datasheet](https://www.st.com/resource/en/datasheet/hts221.pdf)
- [ST LPS25H datasheet](https://www.st.com/resource/en/datasheet/lps25h.pdf)
- [ST LPS25HB datasheet](https://www.st.com/resource/en/datasheet/lps25hb.pdf)
- [ST LSM9DS1 datasheet](https://www.st.com/resource/en/datasheet/lsm9ds1.pdf)
