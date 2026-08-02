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

`EncoderABC` is the minimal hardware boundary for a future GPIO, counter-chip, or
microcontroller-backed encoder implementation. `read_sample()` reports signed
cumulative ticks and a monotonic timestamp. The concrete driver configuration
defines which physical wheel direction is positive.

The interface intentionally does not report wheel distance, speed, or delta
ticks. Those values depend on calibration and consumer history:

- the application derives delta ticks from consecutive cumulative samples;
- ticks per revolution, gear ratio, and wheel radius belong to robot geometry;
- velocity filtering and rejected-edge policy belong to localization or driver
  configuration, respectively.

`reset(ticks=0)` must update the software-visible counter atomically with respect
to edge callbacks and reads. `close()` must stop callbacks and release only the
resources owned by that driver.

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
