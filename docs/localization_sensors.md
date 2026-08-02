# Localization sensor contracts

`robot_hat` keeps hardware acquisition separate from localization algorithms.
Drivers report typed observations in a sensor-local frame; the application owns
mounting transforms, filtering, fusion, wheel geometry, and SLAM state.

## IMU

`IMUABC.read_sample()` returns an immutable `IMUSample` with:

- acceleration in metres per second squared;
- angular velocity in radians per second;
- a process-local `time.monotonic_ns()` observation timestamp.

The axis order is `(x, y, z)`. A concrete driver must document its positive axis
directions. The application must transform that local frame into its robot base
frame instead of hiding board mounting assumptions inside the hardware driver.

`SH3001` defaults to ±2 g and ±2000 degrees/s. Its conversion uses the
manufacturer sensitivity values for those configured ranges and standard gravity
of 9.80665 m/s². `read_raw_sample()` is available for calibration and diagnostics;
normal application code should consume `read_sample()`.

The monotonic timestamp is not Unix time. It is suitable for ordering and fusing
observations acquired in the same process and monotonic clock domain.

## Wheel encoders

`EncoderABC` is the hardware boundary for a GPIO, counter-chip, magnetic, or
microcontroller-backed encoder implementation. `read_sample()` reports signed
cumulative ticks and a monotonic timestamp. The concrete driver configuration
defines which physical wheel direction is positive. `read_health()` reports
availability and cumulative diagnostics without adding vendor-specific fields to
every motion sample.

The interface intentionally does not report wheel distance, speed, or delta
ticks. Those values depend on calibration and consumer history:

- the application derives delta ticks from consecutive cumulative samples;
- ticks per revolution, gear ratio, and wheel radius belong to robot geometry;
- velocity filtering and rejected-edge policy belong to localization or driver
  configuration, respectively.

`reset(ticks=0)` must update the software-visible counter atomically with respect
to edge callbacks and reads. `close()` must stop callbacks and release only the
resources owned by that driver.

### AS5600L cumulative encoder

`AS5600LEncoder` uses the AS5600L's unscaled 12-bit raw-angle register as a
4096-tick/revolution wheel encoder. Its default I²C bus and address are `1` and
`0x40`:

```python
from robot_hat import AS5600LEncoder

encoder = AS5600LEncoder(invert_direction=False)
try:
    encoder.initialize()
    sample = encoder.read_sample()
    health = encoder.read_health()
finally:
    encoder.close()
```

Initialization rejects a missing magnet and the sensor's severe too-weak and
too-strong conditions. Sampling unwraps transitions across 0/4095. A gap longer
than 100 ms is ambiguous because the wheel could have completed an unobserved
rotation; by default the driver preserves the current cumulative count,
re-baselines at the new raw angle, and increments `invalid_transitions`. Configure
`max_sample_gap_ns=None` only when the caller can guarantee that the wheel cannot
move more than half a revolution between samples.

The driver timestamps a sample after its I²C observation using
`time.monotonic_ns()`. Pass an existing `SMBusABC` as `bus` to share an I²C bus;
the encoder will not close an injected bus. It closes only a bus that it created
from a numeric bus ID.

## Absolute angular position and steering

`AngularPositionABC` is distinct from `EncoderABC`: it reports absolute angle
rather than a cumulative multi-turn count. `AS5600LAngularPosition` is suitable
for a steering linkage or steering pivot that does not rotate continuously:

```python
from robot_hat import AS5600LAngularPosition

steering = AS5600LAngularPosition(
    zero_offset_degrees=184.5,
    invert_direction=True,
)
try:
    steering.initialize()
    actual_steering_angle = steering.read_angle()
finally:
    steering.close()
```

The returned angle is normalized to `[0, 360)`. Mounting the magnet and sensor
after the servo gear train, on the linkage or steering pivot, lets the
measurement include servo deadband, backlash, linkage nonlinearity, wheel load,
and calibration error. A sensor on the servo motor shaft cannot observe all of
those effects.

A typical estimator can then combine complementary observations:

- rear wheel encoders provide measured distance;
- actual steering angle predicts curvature;
- an IMU gyroscope measures yaw rate;
- LiDAR localization provides global or local pose corrections.

## AS5600L low-level access and address safety

`AS5600L` exposes raw angle, degrees, magnet status, magnitude, gain, filter
configuration, and a temporary address change. Normal construction and
initialization never issue an OTP command.

Permanent address programming is isolated in `AS5600LAddressProgrammer`. The
AS5600L `BURN_SETTING` command also permanently captures the current `MANG` and
`CONF` registers, and OTP bit changes have one-way constraints. The programmer
therefore requires an exact, address-specific phrase and verifies the OTP
readback:

```python
from robot_hat import AS5600LAddressProgrammer

new_address = 0x42
with AS5600LAddressProgrammer(bus=1, address=0x40) as programmer:
    phrase = programmer.confirmation_phrase(new_address)
    result = programmer.program_address(
        new_address,
        confirmation=phrase,
    )

# Power-cycle only the sensor, then verify using its newly programmed address.
with AS5600LAddressProgrammer(bus=1, address=new_address) as programmer:
    assert programmer.verify_programmed_address(new_address)
```

Do not put this procedure in robot startup. Before using it, provide the power
supply and programming capacitor required by the datasheet, confirm the live
`MANG` and `CONF` values are the settings intended to be permanent, perform the
burn once, then power-cycle and verify. See the
[ams OSRAM AS5600L datasheet](https://look.ams-osram.com/m/657fca3b775890b7/original/AS5600L-DS000545.pdf),
especially the non-volatile memory and I²C address programming sections.

## Hardware-free mocks

`MockEncoder()` and `MockAngularPosition()` require no GPIO or I²C configuration.
Both have stationary, healthy defaults and can be configured with a fixed amount
of motion per sample:

```python
from robot_hat import MockAngularPosition, MockEncoder

left = MockEncoder(ticks_per_sample=4)
steering = MockAngularPosition(
    initial_angle_degrees=180.0,
    degrees_per_sample=0.5,
)
left.initialize()
steering.initialize()
```

The mock health objects leave magnet fields as `None` unless configured, matching
non-magnetic encoder implementations such as a GPIO quadrature encoder.

## Implementing a driver

An implementation should:

- avoid opening hardware during module import;
- inject GPIO, bus, or clock dependencies where practical;
- timestamp as close to the completed hardware observation as possible;
- use immutable samples and the units required by the interface;
- make direction and sensor-local axes explicit;
- be safe to close after partial initialization;
- include hardware-free tests for sign, scaling, counter wrap policy, lifecycle,
  malformed reads, and resource ownership.

SH3001 range and sensitivity reference:
[Senodia product specifications](https://www.senodia.com/product.html).
