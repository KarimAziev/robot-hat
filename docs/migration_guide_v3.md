# Migration guide to v3.0.0

Version 3 makes calibration reporting and hardware-resource ownership explicit.
Custom motor implementations and applications that inspect motor state must be
updated deliberately.

## Upgrade range

Pin the major version so future breaking releases are not installed
accidentally:

```text
robot-hat>=3.0.0,<4
```

The repository uses `setuptools_scm`; a built package becomes exactly `3.0.0`
when the release commit is tagged `v3.0.0`.

## Motor `speed` and `applied_speed`

All motor implementations now expose two distinct values:

- `speed` is the last caller command after constraining it to `max_speed`. It
  does not include wiring-direction calibration or magnitude offset.
- `applied_speed` is the calibrated command represented by the electrical
  output. Its sign includes direction calibration and its magnitude includes
  the non-zero speed offset. It uses the public speed scale, not a chip-specific
  duty-cycle or register unit.

For example:

```python
motor = I2CDCMotor(
    dir_pin=direction_pin,
    driver=pwm_driver,
    channel=0,
    calibration_direction=-1,
    calibration_speed_offset=10,
)
motor.set_speed(20)

assert motor.speed == 20
assert motor.applied_speed == -30
```

In v2, `I2CDCMotor.speed` could expose the calibrated electrical sign. Code
that used `speed` to infer physical output must switch to `applied_speed`. Code
that treats `speed` as requested logical motion can remain unchanged.

For non-PWM `GPIODCMotor`, every non-zero command produces full electrical
output. After `set_speed(30)` with `max_speed=100`, `speed` is `30` while
`applied_speed` is `100` (subject to direction calibration).

Zero is never increased by a calibration offset: both properties become zero
and the backend is stopped. A negative magnitude offset cannot reverse a
non-zero command; it floors the calibrated magnitude at zero.

### Custom `MotorABC` implementations

`applied_speed` is a new abstract property. Custom implementations must store
and expose both states and clear both in `stop()`:

```python
class MyMotor(MotorABC):
    @property
    def speed(self) -> float:
        return self._logical_speed

    @property
    def applied_speed(self) -> float:
        return self._applied_speed
```

`MotorCalibration.apply_calibration()` returns the pair consistently:

```python
logical, applied = self.apply_calibration(command, self.max_speed)
```

## Injected resource ownership

An object no longer silently takes ownership merely because it received a
dependency in its constructor.

- `I2CDCMotor(..., driver=..., dir_pin=...)` defaults to
  `owns_driver=False` and `owns_direction_pin=False`.
- `Servo(driver=...)` defaults to `owns_driver=False`.
- `MotorFactory` owns drivers and pins that it creates. It does not own objects
  supplied through `driver=` or `dir_pin=`.
- `AS5048A` closes only a `SpidevDevice` it creates; injected `SPIABC` devices
  remain caller-owned.

Shared drivers should be closed once, after all consumers:

```python
driver = PWMFactory.create_pwm_driver(config)
left = I2CDCMotor(left_pin, driver, 0)
right = I2CDCMotor(right_pin, driver, 1)
steering = Servo(driver, 2)

try:
    ...
finally:
    left.close()  # stops channel; leaves driver and injected pin open
    right.close()
    steering.close()  # leaves driver open
    left_pin.close()
    right_pin.close()
    driver.close()  # exactly once, last
```

For a deliberate ownership transfer, opt in explicitly:

```python
motor = I2CDCMotor(
    direction_pin,
    dedicated_driver,
    0,
    owns_driver=True,
    owns_direction_pin=True,
)
```

Do not set `owns_driver=True` on multiple consumers sharing one driver.

## I²C discovery

Generic I²C probing cannot be universally safe: some devices interpret reads
or writes as commands, and behavior varies by device state. v3 therefore:

- trusts one explicitly configured address without probing during construction;
- rejects reserved addresses outside `0x08..0x77`;
- uses a read probe for explicit address-list selection and scans instead of a
  dummy write;
- accepts a device-specific probe callback when the protocol defines a known
  safe identity or status read.

Prefer explicit configuration. If discovery is necessary, supply a
device-specific `I2CProbe`. `is_available()` is the supported spelling; the
misspelled `is_avaliable()` API is not present in v3.

## Encoder health contract

`EncoderABC` requires `read_health()`. Custom encoders and test doubles must
return `EncoderHealth`, including communication and invalid-transition counters
where applicable.

## AS5048A support

v3 adds:

- `SPIABC` and Linux `SpidevDevice`;
- parity-checked `AS5048A` register reads and typed SPI error flags;
- magnetic diagnostics, magnitude, raw angle, and degrees;
- `AS5048AEncoder` with 16,384 ticks/revolution and guarded cumulative
  unwrapping;
- `AS5048AAngularPosition` with reversible software zero and direction
  inversion.

Install the Linux backend with `robot-hat[spi]>=3.0.0,<4`. The dependency stays
optional so systems that do not use SPI do not need to build or install
`spidev`.

For macOS or other hardware-free development, call `setup_env_vars()` before
constructing hardware. It selects `MockAS5048ASPI` through
`ROBOT_HAT_MOCK_SPI=1`; importing `robot_hat` never imports `spidev`, and a
default AS5048A constructor uses the emulator instead of a Linux SPI device.
Applications can also inject `MockAS5048ASPI` or the generic queued-response
`MockSPI` explicitly.

See [AS5048A magnetic encoder](./as5048a.md) for wiring, electrical cautions,
usage, ownership, and validation requirements.

## Hardware validation claims

The repository defines an operator-assisted motor HIL procedure and evidence
format. It does not claim a real rig passed until a completed report is
committed under `hardware-validation/evidence/`. Software tests and mocked
buses validate protocol logic but are not physical validation evidence.

## `picar-x-racer`

The companion application has been migrated to require
`robot-hat>=3.0.0,<4`. Its adapter owns one cached PWM driver per bus/address,
loans it to motors and servos, rejects conflicting configurations for the same
device, and closes shared drivers only after their consumers.
