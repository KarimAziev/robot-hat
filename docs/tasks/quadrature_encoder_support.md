# Task: Add Generic Quadrature Encoder Support to `robot-hat`

## Repository

```text
/Users/km/src/robot-hat
```

## Context

The library already has, or another completed workstream has added, the following
related functionality:

- A low-level AS5600L I²C angle driver.
- `AS5600LEncoder`, implementing `EncoderABC`.
- `EncoderHealth`.
- `AngularPositionABC` and `AngularPositionSample`.
- An AS5600L-based absolute steering-angle sensor.
- Configurable mock encoders and angular-position sensors.
- Explicit, isolated AS5600L permanent-address programming.

Inspect the repository and read the surrounding implementation before editing.
Do not overwrite, revert, reformat, stage, or commit unrelated work. Check
`git status` and `git diff` first.

Create a new branch for this work, for example:

```text
feat/quadrature-encoders
```

Do not push. Make one or more focused local commits after implementation and
verification are complete.

## Objective

Add a vendor-neutral quadrature encoder architecture suitable for:

- AS5304B with an off-axis multipole magnetic ring.
- AS5306B with an off-axis multipole magnetic ring.
- TMAG5110 quadrature output.
- Optical ABI encoders.
- Integrated motor encoders.
- Other incremental A/B encoders.

The initial physical target is two rear differential-outdrive encoders on an
RC-style chassis.

Each rear wheel or outdrive has its own encoder. The library must expose each
one independently as an `EncoderABC`. Pairing the left and right encoders and
calculating vehicle odometry belongs in the application, not in `robot-hat`.

The AS5304B and AS5306B provide digital incremental outputs; they are not I²C
angle sensors. Do not create fake register-level drivers for them. Their
differences are primarily magnetic-ring geometry, pole pitch, and allowable
sensor-to-ring gap. A single generic ABI/quadrature implementation should
support both.

Use the official sources as the hardware references:

- [AS5304/AS5306 datasheet](https://look.ams-osram.com/m/6f3f7da07e6fa00/original/AS5304-06-DS000187.pdf)
- [AS5306 product page](https://ams-osram.com/products/sensor-solutions/position-sensors/ams-as5306-linear-sensor)
- [TI TMAG5110](https://www.ti.com/product/TMAG5110)

Do not infer electrical behavior, edge polarity, index semantics, or magnetic
diagnostic semantics from memory. Verify any such behavior against the
official datasheet before encoding it in a public API.

## Required Architecture

Separate these three concerns:

```text
A/B electrical edge source
          |
          v
quadrature counter backend
          | signed cumulative transitions
          v
QuadratureEncoder
          | EncoderSample + EncoderHealth
          v
EncoderABC consumer
```

The counter backend is responsible for observing and decoding electrical
transitions. `QuadratureEncoder` adapts a backend to the public `EncoderABC`
contract.

This separation is important because Python GPIO callbacks may be adequate for
tests and slow encoders, but the rear magnetic-ring encoders can produce
thousands of transitions per second. A future RP2040 PIO, MCU timer, kernel, or
dedicated counter backend must be usable without changing the
application-facing encoder API.

## 1. Add Quadrature Counter Data Types

Add a small immutable snapshot type in a location consistent with the existing
`robot_hat/data_types/` organization.

A conceptual API is:

```python
@dataclass(frozen=True)
class QuadratureCounterSnapshot:
    count: int
    timestamp_monotonic_ns: int
    invalid_transitions: int = 0
```

Requirements:

- `count` is a signed cumulative count.
- The timestamp uses `time.monotonic_ns()`.
- `invalid_transitions` is cumulative since backend construction or
  initialization.
- Validate that timestamps and diagnostic counters are non-negative.
- Document whether `count` is expressed as x1, x2, or x4 counts.
- Do not use wall-clock time.

Add a typed decode-mode enum or equivalent:

```python
class QuadratureDecodeMode(Enum):
    X1 = 1
    X2 = 2
    X4 = 4
```

Avoid loosely typed strings where an enum gives a safer public API.

## 2. Add `QuadratureCounterBackendABC`

Add a backend contract under `robot_hat/interfaces/`, conceptually:

```python
class QuadratureCounterBackendABC(ABC):
    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def read_snapshot(self) -> QuadratureCounterSnapshot: ...

    @abstractmethod
    def reset(self, count: int = 0) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
```

The exact names can be adjusted to fit existing library conventions, but
preserve these semantics:

- Initialization is explicit.
- Snapshot reads are atomic.
- Reset is atomic relative to edge processing and snapshot reads.
- Count is signed and cumulative.
- Invalid transitions are observable.
- Cleanup is idempotent.
- Resources created by the backend are closed by it.
- Injected or shared resources are not closed unless ownership was explicitly
  transferred.
- Sampling before initialization and after close produces clear, typed errors.
- No hardware access occurs at package import time.

The backend contract must remain independent of AS5304B, AS5306B, Raspberry Pi,
GPIO Zero, or a specific co-processor.

## 3. Implement a Pure Quadrature State Decoder

Add a deterministic, hardware-independent quadrature state machine that
accepts A/B states and updates a signed count.

The decoder should use the standard Gray-code state sequence. For example, one
direction is:

```text
00 -> 01 -> 11 -> 10 -> 00
```

The reverse sequence must decrement.

Requirements:

- Support both rotational directions.
- Support x1, x2, and x4 decoding, with precisely documented semantics.
- A repeated state does not change the count and is not necessarily an error.
- A transition where both A and B change simultaneously is invalid.
- Invalid transitions increment a cumulative diagnostic counter.
- Direction inversion must be supported, but it must exist in only one
  well-defined layer. Do not apply inversion in both the backend and
  `QuadratureEncoder`.
- State mutation and reads must be thread-safe.
- Reset must not accidentally reinterpret the next legal electrical
  transition as a full movement.
- The initial A/B state must be established without creating a false count.
- Do not implement software debouncing that discards valid high-frequency
  encoder transitions.
- Keep this decoder independent of GPIO so it can be exhaustively unit-tested.

Prefer a compact transition lookup table over a long collection of
edge-specific conditionals.

## 4. Implement `QuadratureEncoder`

Add a concrete implementation of `EncoderABC`, conceptually:

```python
class QuadratureEncoder(EncoderABC):
    def __init__(
        self,
        *,
        backend: QuadratureCounterBackendABC,
        invert_direction: bool = False,
    ) -> None: ...

    def initialize(self) -> None: ...

    def read_sample(self) -> EncoderSample: ...

    def read_health(self) -> EncoderHealth: ...

    def reset(self, ticks: int = 0) -> None: ...

    def close(self) -> None: ...
```

Requirements:

- Delegate electrical edge counting to the injected backend.
- Return signed cumulative ticks through the existing `EncoderSample`.
- Apply direction inversion consistently.
- Preserve atomic read/reset behavior.
- Propagate the backend's monotonic timestamp.
- Populate generic `EncoderHealth` as follows:
  - `available` reflects initialization, backend health, and closed state.
  - Magnet fields remain `None` unless a concrete backend can actually
    determine them.
  - `invalid_transitions` comes from the counter backend.
  - Communication or backend errors are cumulative.
- Do not pollute every `EncoderSample` with health or hardware-specific fields.
- `close()` must be safe to call more than once.
- If `QuadratureEncoder` owns the injected backend by definition, document that
  clearly. Otherwise, add an explicit ownership option and test both ownership
  modes.
- Avoid swallowing backend exceptions. Count failures and surface an
  appropriate typed exception.

This class must be usable twice, once for the left outdrive and once for the
right outdrive, with entirely independent state.

## 5. Add a Mock Quadrature Backend

Add a deterministic `MockQuadratureCounterBackend` under the existing mock
package.

It should work without Raspberry Pi hardware and have useful zero-argument
defaults.

A reasonable conceptual API is:

```python
backend = MockQuadratureCounterBackend()
backend.initialize()

backend.advance(120)
snapshot = backend.read_snapshot()
assert snapshot.count == 120
```

Useful capabilities:

- Default count of zero.
- Available by default after initialization.
- Manually advance by positive or negative counts.
- Set an absolute count.
- Inject an invalid-transition count.
- Simulate unavailable or failed reads.
- Use a deterministic injected monotonic clock for tests.
- Thread-safe reads, advances, and resets.
- Explicit lifecycle behavior.
- No background threads or sleeps by default.

If `MockEncoder` and `MockAngularPosition` already exist, preserve them. Do not
create competing implementations with nearly identical names. Make the
quadrature mock complementary to the existing public mocks.

## 6. Add a Reference GPIO Backend Only If It Can Be Described Honestly

A software GPIO quadrature backend is useful for low-rate encoders and hardware
experimentation, but it must not be presented as reliable for high-rate
AS5304B/AS5306B rings on a busy Linux system.

If implementing a GPIO backend in this task:

- Name it generically, such as `GPIOQuadratureCounterBackend`.
- Inject the GPIO or pin edge source so tests do not require real hardware.
- Observe both rising and falling edges when using x4 decoding.
- Read A and B as one logical state at every callback.
- Do not use the current `Pin.irq()` default 200 ms debounce.
- Do not add encoder debounce.
- Make cleanup detach callbacks and close only owned pins.
- Test callback detachment and resource ownership.
- Document it as a reference or low-rate backend.
- Explicitly warn that Python callbacks are not appropriate for guaranteed
  high-rate odometry.
- Do not claim that it is a production backend for a ring producing thousands
  of transitions per second.

The existing `robot_hat.pin.Pin.irq()` builds a GPIO Zero `Button` and defaults
to a 200 ms bounce time. Do not silently reuse that behavior for encoder
capture. Either add an appropriate raw-edge abstraction without breaking
existing `Pin.irq()` users, inject a different edge source, or leave the
physical GPIO backend for a separate task.

If implementing it cleanly would require a risky redesign of `Pin`, stop at the
tested backend contract, pure decoder, generic encoder, and mock backend.
Document the next hardware-backend task rather than weakening the abstraction.

## 7. Allow Future Hardware Counters Without Redesign

The public contracts must be able to accommodate future backends such as:

- RP2040 PIO quadrature counter.
- Microcontroller hardware timer or counter.
- Linux kernel or input-event counter.
- Dedicated SPI or I²C counter IC.
- A serial protocol reporting cumulative left and right counts.
- A CAN-connected motor controller reporting position.

Do not implement all of these now.

Do not bake Raspberry Pi GPIO pin numbers into `QuadratureEncoder`. Do not
require callbacks in the backend interface; a hardware backend may simply
return an atomic counter snapshot.

## 8. Handle AS5304B/AS5306B Resolution in Documentation or a Helper

For AS5304/AS5306 multipole rings, distinguish:

- Electrical A/B cycles.
- Quadrature state transitions.
- Mechanical revolutions.
- Magnetic pole pairs.

At x4 decoding, the datasheet's 40 A/B periods per pole pair correspond to 160
quadrature counts per pole pair:

```python
counts_per_revolution = 160 * pole_pairs
```

Examples:

```text
12 pole pairs -> 1,920 x4 counts/revolution
16 pole pairs -> 2,560 x4 counts/revolution
22 pole pairs -> 3,520 x4 counts/revolution
```

Verify this interpretation directly against the official datasheet before
committing documentation or a helper.

If adding a helper, keep it explicit and typed. For example:

```python
def as530x_counts_per_revolution(
    pole_pairs: int,
    decode_mode: QuadratureDecodeMode = QuadratureDecodeMode.X4,
) -> int: ...
```

Do not put wheel diameter, gear ratio, meters per tick, or vehicle geometry in
`robot-hat`. Those belong to the application's odometry configuration.

Do not create a device class that implies AS5304B or AS5306B can be configured
through software registers.

## 9. Optional Index-Channel Preparation

AS530x devices may expose an index output. The architecture should not prevent
later index support.

For this task:

- Do not automatically reset the cumulative count on an index pulse.
- Do not require an index pin.
- If index is supported, make it optional.
- Treat index as a reference event that can be counted or reported.
- Avoid changing the meaning of `EncoderSample.ticks`.
- Ensure an unexpected or noisy index signal cannot silently corrupt odometry.

It is acceptable to leave index capture for a later task if including it would
complicate the core counter contract.

## 10. Keep Pulse/Direction Devices Separate

TMAG5111 exposes speed/pulse and direction behavior rather than the same A/B
interface. Do not force it through a quadrature decoder.

The architecture may eventually add something like:

```python
class PulseDirectionCounterBackendABC(...): ...
```

or:

```python
class PulseDirectionEncoder(EncoderABC): ...
```

That is not required for this first quadrature task.

The generic quadrature work should directly cover AS5304B, AS5306B, TMAG5110,
and conventional ABI encoders.

## 11. Public API and Compatibility

- Preserve `EncoderABC`.
- Preserve `EncoderSample`.
- Preserve `EncoderHealth`.
- Preserve `AngularPositionABC`.
- Preserve AS5600L classes and behavior.
- Do not add hardware-specific fields to `EncoderSample`.
- Update public `__init__.py` exports consistently.
- Avoid circular imports.
- Avoid import-time GPIO or I²C access.
- Remain compatible with Python 3.10.
- Keep Pyright strictness intact; do not solve typing errors with broad `Any`,
  ignores, or unjustified casts.
- Check all existing `EncoderABC` implementations and test doubles after any
  abstract-method changes.

If the existing AS5600L implementation's API needs a small compatibility
adjustment to integrate with the final `EncoderABC`, make the smallest necessary
change and explain it in the commit. Do not redesign or rewrite the AS5600L
driver as part of this task.

## 12. Tests

Use `unittest` and hardware-independent fakes.

At minimum, add tests for the following behavior.

### Decoder Behavior

- Complete forward x4 state sequence.
- Complete reverse x4 state sequence.
- Multiple complete revolutions or sequences.
- Repeated state.
- Every invalid two-bit transition.
- Invalid-transition counter accumulation.
- x1 behavior.
- x2 behavior.
- x4 behavior.
- Direction inversion.
- Initial-state establishment without a false tick.
- Reset followed by legal movement.
- Thread-safe snapshot and reset behavior where practical.

### Backend Behavior

- Read before initialization.
- Initialize twice, or clearly documented idempotence.
- Atomic snapshot.
- Reset to zero.
- Reset to a non-zero signed value.
- Negative counts.
- Close twice.
- Read after close.
- Invalid-transition diagnostics.
- Injected monotonic timestamps.
- Resource ownership and cleanup if a real GPIO backend is included.

### `QuadratureEncoder`

- Implements `EncoderABC`.
- Returns `EncoderSample`.
- Preserves the backend timestamp.
- Positive and negative cumulative counts.
- Direction inversion.
- Reset behavior.
- Communication or backend error counting.
- `EncoderHealth` mapping.
- Magnet health fields are `None`.
- A closed encoder is unavailable.
- Independent left and right instances do not share state.

### Mocks

- Useful zero-argument construction.
- Manual positive and negative advancement.
- Health configuration.
- Error injection.
- Deterministic timestamps.
- Lifecycle behavior.

### Compatibility

- Existing AS5600L encoder tests still pass.
- Existing angular-position tests still pass.
- Existing sensor-contract tests still pass.
- Public exports import successfully without hardware access.

Do not require physical GPIO or I²C hardware in CI.

## 13. Documentation

Add concise user-facing documentation explaining:

- `EncoderABC` represents one signed cumulative encoder.
- AS5600L is an absolute I²C angle sensor that can be software-unwrapped.
- AS5304B and AS5306B are incremental A/B sensors and use
  `QuadratureEncoder`.
- Each rear differential outdrive should get an independent encoder instance.
- Left/right fusion belongs to the application.
- x1/x2/x4 count semantics.
- Counts per mechanical revolution for a multipole ring.
- Direction inversion.
- Why a Python GPIO backend may lose transitions at high speed.
- Why a hardware counter or co-processor is recommended for production
  odometry.
- Index behavior, if supported.
- Resource ownership.
- A minimal mock example.
- A minimal two-encoder construction example.

Example pseudocode:

```python
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

Do not promise that this alone makes the system real-time or guarantees that no
edges will be lost.

## 14. Validation

Run, at minimum:

```bash
make test
make pyright-check
make ruff-format-check
make ruff-lint
git diff --check
```

Prefer:

```bash
make all
```

Report:

- Branch name.
- Commit hashes.
- Files added or changed.
- Tests and checks run.
- Whether a real GPIO backend was implemented or intentionally deferred.
- Known hardware limitations.
- Confirmation that no changes were pushed.
- Confirmation that unrelated pre-existing work was not included in commits.

## Acceptance Criteria

The task is complete when:

- A hardware-independent quadrature decoder exists.
- A vendor-neutral counter-backend ABC exists.
- `QuadratureEncoder` implements the existing `EncoderABC`.
- A deterministic mock backend exists.
- Forward, reverse, x1, x2, x4, and invalid-transition behavior is tested.
- Health and lifecycle behavior are tested.
- The result can represent two independent rear outdrive encoders.
- The public design can later accept a hardware counter without changing
  `EncoderABC`.
- AS5600L and steering-angle support still pass their tests.
- No AS5304B/AS5306B register driver has been invented.
- High-rate limitations of Python GPIO callbacks are documented honestly.
- All required checks pass.
- Changes are committed locally but not pushed.

## Non-Goals

Do not include these in this library task:

- Combining left and right encoder ticks.
- Ackermann or bicycle-model odometry.
- Wheel-radius conversion.
- Gear-ratio conversion.
- Vehicle pose integration.
- IMU fusion.
- LiDAR fusion.
- Frontend telemetry.
- Application configuration migrations.
- Automatic OTP programming.
- A fake AS5304/AS5306 I²C driver.
- Full RP2040 firmware.
- A production SLAM implementation.

Those belong in later application or hardware-backend tasks.

## Follow-Up Application Integration

Once the generic quadrature layer exists, `picar-x-racer` should evolve from a
single encoder stream to explicit left and right rear encoder measurements:

```text
left outdrive encoder  --+
                         +--> average longitudinal distance
right outdrive encoder --+

left/right difference ----> slip and drivetrain diagnostics
actual steering angle ----> predicted Ackermann curvature
IMU yaw rate --------------> short-term rotational correction
LiDAR localization --------> accumulated pose-error correction
```

This boundary should remain clear: `robot-hat` acquires and validates individual
sensor measurements; `picar-x-racer` interprets those measurements as vehicle
motion.
