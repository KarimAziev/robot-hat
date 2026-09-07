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

`LSM9DS1` provides the same six-axis contract for the Raspberry Pi Sense HAT v1
and v2, and for standalone LSM9DS1 devices. The Sense HAT accelerometer/gyroscope
function is wired to I²C bus 1 at `0x6a`; its separately addressed magnetometer at
`0x1c` uses `MagnetometerABC` rather than the six-axis `IMUABC` contract. The IMU driver uses ST's
native X/Y/Z signs without the undocumented application-specific remapping,
calibration, bias learning, or fusion performed by RTIMULib. Its defaults are
±2 g, ±245 degrees/s, and 119 Hz. Pass a shared `SMBusABC` to combine it safely
with other drivers on the bus; closing the IMU does not close an injected bus.
See [Sense HAT environmental and magnetic sensors](sense_hat_sensors.md) for the
magnetometer and remaining Sense HAT sensor devices.

`LSM6DS33` provides the six-axis contract for the corresponding ST sensor on
Pololu's MiniIMU-9 v5 and AltIMU-10 v5, as well as standalone LSM6DS33 carriers.
It defaults to I²C address `0x6b`, ±2 g, ±245 degrees/s, and 104 Hz. The
independent `LIS3MDL` driver provides magnetic samples in teslas at address
`0x1e`. Driving the Pololu board's shared `SA0` pin low changes those addresses
to `0x6a` and `0x1c`, respectively. Both drivers expose native axes, typed
configuration, diagnostic raw counts, and caller-owned shared-bus injection.
See [Pololu MiniIMU-9 v5 support](pololu_miniimu9_v5.md) for wiring, complete
configuration ranges, and calibration responsibilities.

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

### AS5048A absolute magnetic encoder

For the 14-bit SPI/PWM AS5048A, use `AS5048AEncoder` for cumulative ticks or
`AS5048AAngularPosition` for absolute degrees. The SPI driver validates parity,
reports protocol and magnetic faults, and avoids permanent OTP programming.
See [AS5048A magnetic encoder](./as5048a.md) before wiring a marketplace
breakout, because a `+5V` module label does not prove Raspberry Pi-safe logic
levels.

### Incremental A/B quadrature encoders

`QuadratureEncoder` adapts one vendor-neutral
`QuadratureCounterBackendABC` to `EncoderABC`. It can represent an AS5304B,
AS5306B, TMAG5110, optical ABI encoder, integrated motor encoder, or another
incremental A/B source without putting GPIO pins, callbacks, or vendor details
in the application-facing encoder API. AS5304B and AS5306B are digital
incremental sensors, not I²C devices; they have no software-register driver in
this package.

The three decode modes describe counts per complete electrical A/B cycle:

- `QuadratureDecodeMode.X1`: one count per complete A/B cycle;
- `QuadratureDecodeMode.X2`: one count per half-cycle;
- `QuadratureDecodeMode.X4`: one count for every legal Gray-code transition.

The positive electrical sequence is `00 -> 01 -> 11 -> 10 -> 00`; reverse
movement subtracts counts. `QuadratureEncoder(invert_direction=True)` reverses
the public tick sign without changing backend behavior. This is the only layer
that applies configured direction inversion.

The AS5304/AS5306 datasheet specifies 40 A/B periods and 160 interpolated
positions per magnetic pole pair. Therefore:

```python
counts_per_revolution = 40 * decode_mode.value * pole_pairs
```

At x4 this is `160 * pole_pairs`: a ring with 12, 16, or 22 pole pairs produces
1,920, 2,560, or 3,520 counts per mechanical revolution, respectively. The
typed `as530x_counts_per_revolution()` helper performs this calculation. These
counts describe sensor-ring rotation only; wheel diameter, drivetrain ratio,
distance per tick, and vehicle geometry remain application configuration.
The sensor mechanics still differ: AS5304 uses a 4.0 mm pole-pair length and a
recommended magnet-to-package gap up to 0.8 mm, while AS5306 uses 2.4 mm and up
to 0.4 mm. Those mounting constraints do not change the counter API.

Each rear outdrive needs an independent backend and encoder instance. The
application combines left and right measurements for distance, slip detection,
or odometry:

```python
from robot_hat import (
    MockQuadratureCounterBackend,
    QuadratureEncoder,
)

left_counter = MockQuadratureCounterBackend()
right_counter = MockQuadratureCounterBackend()
left_encoder = QuadratureEncoder(
    backend=left_counter,
    invert_direction=False,
)
right_encoder = QuadratureEncoder(
    backend=right_counter,
    invert_direction=True,
)

left_encoder.initialize()
right_encoder.initialize()

left = left_encoder.read_sample()
right = right_encoder.read_sample()
```

`QuadratureEncoder` owns and closes its backend by default. Set
`owns_backend=False` only when lifecycle is managed elsewhere. A backend in turn
closes hardware resources it created, while injected or shared resources remain
open unless ownership was explicitly transferred. Generic quadrature health
reports backend availability and invalid transitions; magnet-specific fields
remain `None` unless a future concrete backend can genuinely determine them.

For low-rate experiments, `GPIOZeroDigitalEdgeInput` and
`GPIOQuadratureCounterBackend` observe both signal edges without software
debounce:

```python
from robot_hat import (
    GPIOQuadratureCounterBackend,
    GPIOZeroDigitalEdgeInput,
    QuadratureEncoder,
)

counter = GPIOQuadratureCounterBackend(
    a_input=GPIOZeroDigitalEdgeInput("GPIO17", pull_up=True),
    b_input=GPIOZeroDigitalEdgeInput("GPIO27", pull_up=True),
)
encoder = QuadratureEncoder(backend=counter, invert_direction=False)
encoder.initialize()
```

Use suitable external 3.3 V pull-ups for open-drain sensor outputs; internal GPIO
pull-ups are primarily convenient for initial testing. Never connect a 5 V
push-pull encoder output directly to a 3.3 V Raspberry Pi GPIO. The existing
`Pin.irq()` debounce behavior remains unsuitable for encoder capture, so this
backend uses a separate raw-edge input adapter with `bounce_time=None`.

This remains a reference and low-rate backend. Python callbacks on a busy Linux
system cannot guarantee that they will observe every high-rate edge from an
AS5304/AS5306 ring. Production odometry should use a hardware counter, RP2040
PIO, microcontroller timer, kernel facility, dedicated counter IC, or controller
that returns atomic cumulative snapshots. `QuadratureEncoder` can use such a
backend without changing the application. The GPIO API does not promise
real-time capture or freedom from lost edges.

AS5304/AS5306 index capture is not implemented. An index is a separate reference
event and must never silently reset `EncoderSample.ticks`; a future backend can
report index diagnostics separately without changing cumulative tick meaning.
TMAG5110's two independent latch outputs fit the quadrature architecture.
TMAG5111 provides pulse and direction outputs and should use a separate future
pulse/direction backend rather than this decoder.

Hardware details and resolution are based on the official
[AS5304/AS5306 datasheet](https://look.ams-osram.com/m/6f3f7da07e6fa00/original/AS5304-06-DS000187.pdf),
[AS5306 product page](https://ams-osram.com/products/sensor-solutions/position-sensors/ams-as5306-linear-sensor),
and [TI TMAG5110 documentation](https://www.ti.com/product/TMAG5110).

### AS5600L cumulative encoder

`AS5600LEncoder` software-unwraps the AS5600L absolute I²C angle sensor's
unscaled 12-bit raw-angle register as a 4096-tick/revolution cumulative encoder.
Its default I²C bus and address are `1` and `0x40`:

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
too-strong conditions. Sampling unwraps transitions across 0/4095, which is safe
only when the shaft moves less than half a revolution between reads. The default
`max_abs_speed_rps=5.0` derives a 100 ms maximum unambiguous interval; configure
this value from the real maximum shaft speed. `max_sample_gap_ns` may impose a
stricter scheduling limit. Reaching either limit preserves the current count,
re-baselines, and increments `invalid_transitions`.

Passing `max_abs_speed_rps=None` disables the physical-speed-derived limit.
Passing both that and `max_sample_gap_ns=None` disables all gap protection and is
safe only when the caller independently guarantees less than half a turn per
sample. A single-turn absolute sensor cannot distinguish a large forward turn
from the shorter reverse turn. Prefer a continuously counted quadrature backend
for high-speed wheel or outdrive odometry.

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

The returned angle is normalized to `[0, 360)`. It is an absolute linkage or
pivot bearing, not yet an estimator-ready signed road-wheel angle. The
application must subtract its calibrated center, wrap into a signed range, apply
direction and mechanical ratio, and optionally interpolate a linkage calibration
curve before converting to radians. Mounting the magnet and sensor
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
`CONF` registers, and OTP bit changes have one-way constraints. The sensor must
be power-cycled and isolated on the bus first. The programmer returns an
immutable plan containing every affected value, then re-reads and compares the
live state before accepting an exact plan-specific phrase:

```python
from robot_hat import AS5600LAddressProgrammer

new_address = 0x42
with AS5600LAddressProgrammer(bus=1, address=0x40) as programmer:
    plan = programmer.prepare_address_programming(new_address)
    print(plan)  # Physically verify address, CONF, MANG, and ZMCO before burn.
    result = programmer.program_address(
        plan,
        confirmation=plan.confirmation_phrase,
    )

# Power-cycle only the sensor, then verify using its newly programmed address.
with AS5600LAddressProgrammer(bus=1, address=new_address) as programmer:
    assert programmer.verify_programmed_address(new_address)
```

Do not put this procedure in robot startup. The plan rejects same-address burns,
incompatible one-way OTP address changes, nonzero `ZMCO`, and live settings that
changed after review. Before using it, provide the power supply and programming
capacitor required by the datasheet, confirm that the plan's `MANG` and `CONF`
values are intended to be permanent, perform the burn once, then power-cycle and
verify. See the
[ams OSRAM AS5600L datasheet](https://look.ams-osram.com/m/657fca3b775890b7/original/AS5600L-DS000545.pdf),
especially the non-volatile memory and I²C address programming sections.

## Hardware-free mocks

`MockEncoder()`, `MockQuadratureCounterBackend()`, `MockAngularPosition()`,
`MockIMU()`, and `MockLidar2D()` require no GPIO, I²C, SPI, or UART
configuration. They have stationary or uniform healthy defaults and can be
controlled deterministically:

```python
from robot_hat import (
    MockAngularPosition,
    MockEncoder,
    MockIMU,
    MockLidar2D,
    MockQuadratureCounterBackend,
)

left = MockEncoder(ticks_per_sample=4)
imu = MockIMU(angular_velocity_radps=(0.0, 0.0, 0.2))
lidar = MockLidar2D(distance_m=2.0, scan_frequency_hz=10.0)
counter = MockQuadratureCounterBackend(monotonic_ns=lambda: 42)
steering = MockAngularPosition(
    initial_angle_degrees=180.0,
    degrees_per_sample=0.5,
)
left.initialize()
counter.initialize()
counter.advance(120)
assert counter.read_snapshot().count == 120
steering.initialize()
```

`MockLidar2D` repeats complete revolutions and waits interruptibly at the
configured scan frequency, so it exercises the same blocking iterator contract
as physical scanners without delaying shutdown. Use `set_uniform_scan()` to
move a synthetic wall toward or away from the robot. `MockIMU.set_sample()` can
change acceleration and angular velocity while a publisher is running.

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
