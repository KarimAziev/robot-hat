# Changelog

## v2.2.0 (2025-10-16)

### Added
- INA260 driver, configuration dataclass, and battery service, plus an updated example showing continuous readings.
- Battery factory with config dataclasses covering INA219, INA226, INA260, and the legacy Sunfounder helper.
- Unit tests for INA260 support and the new battery factory.

### Changed
- README updated with INA260 information and battery factory usage.

## v2.1.0 (2025-10-09)

Added support for INA226.

## v2.0.0 (2025-09-20)

⚠️ Major, breaking release. Most public modules, classes, and import paths were moved, renamed, or generalized. Read the [Migration Guide](./docs/migration_guide_v2.md) before upgrading.

### Why this release

Prior versions assumed SunFounder’s stack everywhere. Extending to other PWM chips (PCA9685), batteries (INA219), IMUs, or GPIO-only solutions required copy/paste.
v2 introduces ABC interfaces (`ServoABC`, `MotorABC`, `PWMDriverABC`, etc.) and plug-in factories so that any driver can be dropped in without touching the rest of the stack.
Centralized I2C bus management and retry logic reduces timeouts, resource leaks, and flaky behavior.
A backward-compatible SunFounder path is preserved under `robot_hat.sunfounder.*` while the recommended path uses the new driver architecture.

### Breaking changes

- Package refactor
  - Layered architecture: `drivers`, `services`, `interfaces`, `sensors`, `data_types`, `factories`, `i2c`, `sunfounder` (legacy-friendly), etc.
  - Many classes moved/renamed. See Migration Guide for mappings and examples.
- Servo API
  - New generic servo class `robot_hat.servos.servo.Servo` (driver-based). The former `robot_hat.servo.Servo` moved to `robot_hat.sunfounder.sunfounder_servo.Servo`.
  - `ServoService` now requires a `ServoABC` instance: `ServoService(servo=..., name=...)`. Optional `reverse` flag added.
  - Calibration is applied after constraining the angle to `[min_angle, max_angle]`.
  - SunFounder servo now requires float angles.
- Motor API
  - Replaced `Motor`/`MotorFabric`/`MotorConfig` with dataclass configs and multiple motor implementations:
    - `I2CDCMotor` (PWM driver over I2C + direction Pin)
    - `GPIODCMotor` (direct GPIO)
    - `PhaseMotor` (phase/enable)
  - `MotorFabric` renamed to `MotorFactory`. `create_motor_pair` now accepts dataclass configs (`I2CDCMotorConfig`, `GPIODCMotorConfig`, `PhaseMotorConfig`).
  - `MotorService` works with `MotorABC` implementations and has `close()`.
- I2C stack
  - Old I2C replaced internally with `i2c/i2c_manager.I2C`; top-level `robot_hat.I2C` remains.
  - New abstractions: `I2CBus`, `SMBusManager`. Unified retry decorator.
  - I2C address resolution now raises `I2CAddressNotFound` (was `ADCAddressNotFound` in the old I2C class).
- SunFounder compatibility
  - Legacy SunFounder PWM moved to `robot_hat.sunfounder.pwm.PWM`. Recommended: use `robot_hat.drivers.pwm.sunfounder_pwm.SunfounderPWM` via `PWMFactory`.
  - `reset_mcu_sync` moved to `robot_hat.sunfounder.utils` and now accepts an optional `pin` argument (default `5`).
  - `get_value_description` removed. `get_address_description` resides under `robot_hat.sunfounder.address_descriptions`.
- Pin naming
  `Pin` now accepts not only Sunfounder mappings (prefixed with "D") but also gpiozero-recognized names. You can also pass your own mapping into Pin using the pin_dict parameter. This should be a dictionary of pin names and GPIO numbers.

  If you wish to use physical (BOARD) numbering, you can specify the pin number as "BOARD11", or you can specify pins as "header:number" (e.g., "J8:11"), meaning physical pin 11 on header J8 (the GPIO header on modern Pis).

  You can also use wiringPi pin numbering (another physical layout) by using the "WPI" prefix, e.g., "WPI0".

  Hence, the following lines are all equivalent:

  ```python
  pin = Pin(17)
  pin = Pin("GPIO17")
  pin = Pin("BCM17")  # Broadcom numbering
  pin = Pin("D0")     # Sunfounder numbering
  pin = Pin("BOARD11")  # physical numbering
  pin = Pin("J8:11")    # physical numbering
  pin = Pin("WPI0")     # wiringPi numbering
  ```

### Added

- New drivers
  - `PCA9685` (`robot_hat.drivers.pwm.pca9685.PCA9685`)
  - `SunfounderPWM` (`robot_hat.drivers.pwm.sunfounder_pwm.SunfounderPWM`)
  - SunFounder ADC (`robot_hat.drivers.adc.sunfounder_adc.ADC`)
  - `INA219` (`robot_hat.drivers.adc.INA219` + `data_types/config/ina219.py`)
- New services and sensors
  - Battery services: SunFounder ADC-based and INA219-based.
  - IMU: `SH3001` (`robot_hat.sensors.imu.sh3001.SH3001`)
  - Ultrasonic organized under `sensors/ultrasonic`; top-level alias preserved (`from robot_hat import Ultrasonic`).
- Bus management
  - `SMBusManager`/`I2CBus`: shared bus instances and lifecycle events.
- New abstractions and infra
  - Interfaces: `ServoABC`, `MotorABC`, `PWMDriverABC`, `SMBusABC`, `BatteryABC`, `AbstractIMU`
  - Factories: `PWMFactory` (with `@register_pwm_driver`), `MotorFactory`
  - I2C: `I2CBus`, `SMBusManager`, `retry_decorator`
  - Utils: `get_gpio_factory_name`, `setup_env_vars`
- New servo
  - `GPIOAngularServo` (`robot_hat.servos.gpio_angular_servo.GPIOAngularServo`) for direct GPIO control via gpiozero.
- Convenience exports
  - Top-level aliases like `SunfounderPWM`, `SunfounderADC`, `SunfounderBattery` are available for convenience.

### Changed

- Best practice: explicitly set the PWM frequency on drivers (e.g., `driver.set_pwm_freq(config.freq)`). `PCA9685` requires this; `SunfounderPWM` defaults to 50 Hz but explicit calls are recommended.
- `Pin` now accepts not only Sunfounder's mapping (D2, D3 etc), but convient `gpiozero` mappings. It uses gpiozero’s `Device.pin_factory` to resolve names; works across real hardware and mock environments (see `utils.setup_env_vars`). If you wish to use physical (BOARD) numbering you can specify the pin number as "BOARD11”. If you are familiar with the wiringPi pin numbers (another physical layout) you could use "WPI0” instead. Finally, you can specify pins as "header:number”, e.g. "J8:11” meaning physical pin 11 on header J8 (the GPIO header on modern Pis). See also `gpiozero` [documentation](https://gpiozero.readthedocs.io/en/stable/recipes.html#pin-numbering).

- `get_address_description` is available via `robot_hat.sunfounder.address_descriptions`.

### Removed

- `get_value_description` (rarely useful in logs). Use `get_address_description` as needed.

### Migration tips

- Servos
  - SunFounder servos require float angles.
  - `ServoService` now takes `servo=ServoABC` and a `name`.
  - Re-tune `ServoService.calibration_offset` due to calibration-after-constraint ordering.
  - For driver-based servos (`PCA9685`, `SunfounderPWM`), call `driver.set_pwm_freq(config.freq)` before use.
- Motors
  - Replace `MotorConfig`/`MotorFabric` with dataclass configs and `MotorFactory` (`I2CDCMotorConfig`, `GPIODCMotorConfig`, `PhaseMotorConfig`).
  - `MotorService.close()` now releases resources; use it or context managers where available.
- I2C
  - Catch `I2CAddressNotFound` for open failures.
  - Prefer shared buses via `SMBusManager.get_bus(bus)` and pass to `PWMFactory.create_pwm_driver(bus=...)`.

### Migration tips

- SunFounder servos require float angles.
- ServoService now takes servo=ServoABC and requires a name.
- Re-tune ServoService.calibration_offset due to calibration-after-constraint ordering.
- Update exception handling: catch I2CAddressNotFound for I2C open failures.
- Prefer shared buses via SMBusManager.get_bus(bus) and pass to PWMFactory.create_pwm_driver(bus=...).
