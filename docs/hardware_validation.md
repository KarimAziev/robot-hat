# Hardware-in-the-loop validation

Unit tests validate register traffic and GPIO/PWM decisions against mocks, but
they cannot establish wiring polarity, actual shaft direction, electrical stop
behavior, bus signal integrity, or compatibility with a physical controller.
Those claims require a real rig and retained evidence.

## Current evidence status

No passing HIL report is committed to this repository yet. Do not interpret the
presence of the runner or a mocked test result as physical validation. Reviewed
reports produced on real hardware belong under `hardware-validation/evidence/`.

## Motor validation runner

`tools/hil_motor_check.py` performs three low-speed checks:

1. a positive logical command turns in the rig's expected direction;
2. changing `calibration_direction` reverses that physical direction;
3. `set_speed(0)` remains stopped with a non-zero speed offset.

The runner always issues `stop()` before and after motion, limits speed to 30%,
limits each pulse to two seconds, refuses to run without an explicit risk
acknowledgement, and refuses to overwrite an existing report. These guards
reduce risk; they do not make an unrestrained robot safe.

Before running:

- lift all driven wheels clear of the work surface;
- restrain the chassis and keep hands, hair, cables, and tools clear;
- make the hardware emergency stop or power disconnect immediately reachable;
- verify the configured pins, bus, address, PWM channel, voltage, and current
  limit against the actual rig;
- use a unique rig ID and identify the operator honestly.

Create a configuration file such as:

```json
{
  "motor_type": "i2c_dc",
  "config": {
    "calibration_direction": 1,
    "name": "left_motor",
    "max_speed": 100,
    "driver": {
      "name": "PCA9685",
      "bus": 1,
      "address": 64,
      "frame_width": 20000,
      "freq": 50
    },
    "channel": 0,
    "dir_pin": "D4"
  }
}
```

Then run from the repository root:

```bash
python tools/hil_motor_check.py \
  --config /path/to/rig-left-motor.json \
  --output hardware-validation/evidence/2026-08-28-rig-a-left.json \
  --operator "Operator name" \
  --rig-id "rig-a" \
  --acknowledge-motion-risk
```

The JSON report records observations, exact config and its SHA-256 digest,
package version, Git revision and dirty state, host details, operator, rig, and
UTC timestamps. A passing report should be reviewed before commit. Reject a
report if it was generated with mocks, on an unidentifiable rig, from unrelated
source, with a dirty tree whose changes are not archived, or without observing
all three checks.

Repeat the run for every supported motor backend and materially distinct motor
controller/hat combination. Direction and stop checks should also be repeated
after changes to GPIO mapping, PWM conversion, calibration math, factory
ownership, I²C access, or cleanup behavior.

## I²C validation scope

Generic address discovery is not a sufficient HIL test. There is no universally
side-effect-free I²C probe: writes can issue commands, while reads can consume
FIFO/status data or advance device state. Validate each device through a
documented identity register or a benign operation defined by its datasheet,
then test its actual register reads/writes. Avoid generic scans on a populated
live bus unless every attached device's response is understood.
