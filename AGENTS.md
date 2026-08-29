# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

`robot_hat` is a Python 3.10+ library for controlling robotics hardware such as
motors, servos, ultrasonic sensors, ADC devices, PWM drivers, and I2C buses. The
codebase is designed around explicit interfaces, typed configuration dataclasses,
dependency injection for hardware access, and mockable hardware boundaries for
tests.

This is a hardware-facing package. Treat behavior changes carefully: a small
change to motor direction, PWM values, calibration, I2C register access, or GPIO
setup can affect real devices.

## Repository Layout

- `robot_hat/`: package source.
- `robot_hat/interfaces/`: abstract interfaces for motors, servos, batteries,
  PWM drivers, IMUs, and SMBus-like buses.
- `robot_hat/data_types/`: typed dataclasses and shared type aliases.
- `robot_hat/drivers/`: low-level ADC and PWM drivers.
- `robot_hat/motor/`, `robot_hat/servos/`, `robot_hat/sensors/`: concrete
  hardware implementations.
- `robot_hat/services/`: higher-level orchestration APIs.
- `robot_hat/factories/`: object construction helpers for configured hardware.
- `robot_hat/mock/`: test doubles and mock hardware support.
- `tests/`: `unittest` test suite.
- `docs/`: user-facing migration and project documentation.

## Development Commands

Run checks from the repository root.

```bash
make test
make pyright-check
make ruff-format-check
make ruff-lint
make all
```

Command details:

- `make test`: runs `python -m unittest discover`.
- `make pyright-check`: runs `pyright ./tests ./robot_hat`.
- `make ruff-format-check`: checks formatting with Ruff.
- `make ruff-lint`: runs Ruff lint checks.
- `make all`: runs tests, Pyright, formatting check, and linting.

The Makefile activates `.venv/bin/activate` automatically when that virtualenv
exists. If dependencies are missing, install the package and dev tools in the
project environment before running checks.

## Typing And Pyright

Typing is a core quality requirement for this project, not optional polish. The
library is intended to be safe and maintainable in larger robotics projects, and
strong types are part of that public contract.

When editing Python code:

- Preserve and improve type annotations on public APIs, constructors,
  properties, factory methods, service methods, and hardware interfaces.
- Keep dataclass fields, type aliases, `Literal` values, and interface return
  types precise. Avoid widening a type to `Any`, `object`, or a loose union
  unless the runtime behavior truly requires it.
- Do not silence Pyright errors with ignores or casts before understanding the
  type problem. Prefer fixing the model, narrowing the type, or updating the
  interface.
- Keep tests type-checkable too. `make pyright-check` checks both `robot_hat`
  and `tests`.
- When a dependency is optional, platform-specific, or hardware-specific, model
  that boundary explicitly with protocols, ABCs, dependency injection, or local
  imports rather than weakening package-wide types.
- Preserve typed hardware abstractions such as `SMBusABC`, `PWMDriverABC`,
  `MotorABC`, `ServoABC`, and config dataclasses.

Always run `make pyright-check` after code changes that affect Python source or
tests. If Pyright cannot be run in the current environment, report that clearly
and explain why.

## Code Style

- Target Python 3.10 syntax and semantics.
- Use Ruff formatting and linting. The project line length is 88.
- Prefer standard-library dataclasses and explicit type aliases already present
  in the codebase.
- Keep imports straightforward. Avoid import-time hardware side effects where
  possible.
- Keep public exports in `robot_hat/__init__.py` synchronized when adding,
  renaming, or removing public API objects.
- Use package-local abstractions before introducing new dependencies or new
  framework patterns.
- Use `logging` for diagnostics instead of printing from library code.
- Keep comments focused on hardware behavior, calibration math, non-obvious
  register details, or platform-specific constraints.

## Hardware Boundaries

- Do not require `sudo` or shelling out for normal library behavior.
- Avoid making real GPIO, I2C, PWM, or audio calls during import.
- Prefer dependency injection for buses, drivers, and pins so tests can use
  mocks.
- Every new platform-specific hardware feature should provide an injectable
  boundary and a reusable deterministic test double under `robot_hat/mock/` so
  applications can exercise it during local development without Raspberry Pi
  hardware. When the library has an automatic non-Raspberry-Pi mock mode, keep
  that mode synchronized with new bus types and document its environment
  variables.
- Do not import optional platform modules such as `spidev` at package import
  time. Import them only when constructing the real backend, after any mock
  selection has occurred.
- Be careful with ownership and cleanup. If code creates a bus or hardware
  resource, it should close only resources it owns.
- Keep Raspberry Pi and platform-specific behavior isolated behind helpers or
  local imports.
- Preserve existing mock support, including `ROBOT_HAT_MOCK_SMBUS` and
  `GPIOZERO_PIN_FACTORY=mock` behavior.

## Testing Guidance

- Add or update focused `unittest` coverage for behavior changes.
- Use mocks or fake bus objects for hardware interactions; tests should not
  require real Raspberry Pi hardware.
- For low-level drivers, assert register writes, reads, conversions, and
  configuration values.
- For motors and servos, test calibration, direction, speed bounds, and stop or
  cleanup behavior.
- For factories, test type dispatch, injected dependencies, and error cases.
- Keep tests deterministic and avoid sleeps unless timing behavior is the thing
  under test.

## Documentation

- Update `README.md`, `CHANGELOG.md`, or `docs/` when public behavior,
  installation, migration guidance, or examples change.
- Keep examples typed and consistent with the public API exported from
  `robot_hat/__init__.py`.
- Hardware examples should be clear about required bus numbers, addresses, pins,
  and mock setup when relevant.

## Change Discipline

- Keep changes narrowly scoped to the requested behavior.
- Do not rewrite unrelated modules or reformat untouched files.
- Do not revert user changes in a dirty worktree.
- Before finishing code changes, prefer running `make all`. At minimum, run the
  most relevant tests plus `make pyright-check`.
