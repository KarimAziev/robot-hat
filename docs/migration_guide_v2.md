# MIGRATION GUIDE to version v2

Until now, Robot-Hat assumed Sunfounder's stack everywhere. Supporting other PWM chips (e.g., PCA9685), batteries (INA219), IMUs, or simple GPIO solutions has required copy-pasting large chunks of code.

The new release introduces ABC interfaces (`ServoABC`, `MotorABC`, `PWMDriverABC`, etc.) and plug-in factories so that any driver can be dropped in without touching the rest of the stack. You can also register your own drivers.

A backward-compatible path for existing Sunfounder setups is preserved: most legacy modules are moved to `robot_hat.sunfounder.*`, while the recommended path uses the new driver architecture.

## General approach

- Replace concrete classes with ABC-based implementations and factories.
- Move Sunfounder-specific APIs to `robot_hat.sunfounder.*` OR switch to the new driver-based classes.
- Share your I2C bus via `SMBusManager` where possible to avoid device contention.
- Update imports across your codebase using the mappings shown below.

## Top-level imports

**Old:**

```python
from robot_hat import (
    ADC,
    Servo,
    ADXL345,
    get_address_description,
    get_value_description,
    reset_mcu,
    reset_mcu_sync,
    run_command,
    get_firmware_version,
    Robot,
    PWM,
    Motor,
    MotorFabric,
    MotorConfig,
    Battery,
)
```

> [!NOTE]
>
> `get_value_description` has been removed (it was not useful).
> `MotorConfig` was removed in favor of multiple dataclass configs and multiple motor implementations:
>
> - `I2CDCMotor` (PWM driver over I2C + direction Pin)
> - `GPIODCMotor` (direct GPIO)
> - `PhaseMotor` (phase/enable)
>
> Other changes:
>
> - `MotorFabric` is renamed to `MotorFactory`. `create_motor_pair` now takes dataclass configs (`I2CDCMotorConfig`, `GPIODCMotorConfig`, or `PhaseMotorConfig`).
> - `MotorService` now works with `MotorABC` implementations and exposes a `close()` method.

**New:**

```python
from robot_hat import (
    MotorService,
    SunfounderBattery,    # ADC-based battery helper
    INA219Battery,       # INA219-based battery helper
    SunfounderPWM,       # PWM driver (I2C)
    PCA9685,             # PWM driver (I2C)
    PWMFactory,          # factory for PWM drivers
    MotorFactory,        # factory for motors
    SMBusManager,        # share an I2C bus instance
    Ultrasonic,          # top-level re-export of HC-SR04 class
)
from robot_hat.drivers.adc.sunfounder_adc import ADC as SunfounderADC
from robot_hat.sunfounder import (
    ADXL345,
    PWM,
    Motor,
    Robot,
    get_address_description,
    get_firmware_version,
    reset_mcu,
    reset_mcu_sync,
    run_command,
)
```

> [!NOTE]
>
> - The canonical I2C helper is now `robot_hat.i2c.i2c_manager.I2C` (also re-exported at the top level as `robot_hat.I2C`).
> - The “address not found” exception for I2C is now `I2CAddressNotFound`. If you were catching `ADCAddressNotFound` for general I2C operations, update it.

## Sunfounder

Replace old imports that referenced the top-level package with the new, more specific paths.

**Old:**

```python
from robot_hat.adc import ADC
```

**New:**

```python
from robot_hat.drivers.adc.sunfounder_adc import ADC
# Or convenience alias:
from robot_hat import SunfounderADC
```

**Old:**

```python
from robot_hat.accelerometer import ADXL345
```

**New:**

```python
from robot_hat.sunfounder.accelerometer import ADXL345
```

**Old:**

```python
from robot_hat.robot import Robot
```

**New:**

```python
from robot_hat.sunfounder.robot import Robot
```

**Old:**

```python
from robot_hat.utils import compose, constrain, get_firmware_version, is_raspberry_pi, mapping
```

**New:**

```python
from robot_hat.sunfounder.utils import get_firmware_version, reset_mcu_sync, run_command
from robot_hat.utils import compose, constrain, is_raspberry_pi, mapping
```

**Old:**

```python
from robot_hat.address_descriptions import get_address_description
```

**New:**

```python
from robot_hat.sunfounder.address_descriptions import get_address_description
```

**Old:**

```python
from robot_hat.battery import Battery
```

**New:**

```python
from robot_hat.services.battery.sunfounder_battery import Battery
```

**Old:**

```python
from robot_hat.pwm import PWM
```

Legacy Sunfounder PWM class moved to `robot_hat.sunfounder.pwm.PWM` (kept for compatibility):

```python
from robot_hat.sunfounder.pwm import PWM
```

Recommended: use new driver-based SunfounderPWM via `PWMFactory`:

```python
from robot_hat.drivers.pwm.sunfounder_pwm import SunfounderPWM
# Or:
from robot_hat import SunfounderPWM
```

**Old:**

```python
from robot_hat.grayscale import Grayscale
```

**New:**

```python
from robot_hat.sunfounder.grayscale import Grayscale
```

**Old:**

```python
from robot_hat.pin_descriptions import pin_descriptions
```

**New:**

```python
from robot_hat.sunfounder.pin_descriptions import pin_descriptions
```

**Old:**

```python
from robot_hat.ultrasonic import Ultrasonic
```

**New:**

```python
from robot_hat.sensors.ultrasonic.HC_SR04 import Ultrasonic
# Recommended: keep using the top-level re-export:
from robot_hat import Ultrasonic
```

# Servos

Old code passed a pin to `ServoService`. The new API requires a servo object (implementing `ServoABC`).

**Old**:

```python
from robot_hat import ServoCalibrationMode, ServoService

steering_servo = ServoService(
    servo_pin="P2",
    min_angle=-30,
    max_angle=30,
    calibration_mode=ServoCalibrationMode.SUM,
    calibration_offset=-14.4,
)
```

> [!IMPORTANT]
> Note on servo calibration order:
> Calibration now applies after constraining the angle to [min_angle, max_angle]. If your neutral points shifted, re-tune `calibration_offset`.

You have two approaches: recommended driver-based servos, or legacy Sunfounder-style servos (kept for compatibility).

**New (recommended: driver-based servo)**:

```python
from robot_hat import (
    PWMDriverConfig,
    PWMFactory,
    Servo,                 # driver-based servo
    ServoCalibrationMode,
    ServoService,
    SMBusManager,
    SunfounderPWM,
)

pwm_config = PWMDriverConfig(
    name=SunfounderPWM.DRIVER_TYPE,  # or "Sunfounder"
    address=0x14,                    # I2C address of the device
    bus=1,                           # I2C bus number
    # Optional parameters (defaults provided):
    frame_width=20000,
    freq=50,
)

bus = SMBusManager.get_bus(pwm_config.bus)  # shared bus (returns I2CBus wrapper)
driver = PWMFactory.create_pwm_driver(
    config=pwm_config, bus=bus
)

driver.set_pwm_freq(pwm_config.freq)

steering_servo = ServoService(
    name="steering",
    servo=Servo(
        driver=driver,
        channel="P1",  # Integer or string with numeric suffix
        min_angle=-90.0,
        max_angle=90.0,
        min_pulse=500,
        max_pulse=2500,
        real_min_angle=-90.0,
        real_max_angle=90.0,
    ),
    min_angle=-90,
    max_angle=90,
    calibration_mode=ServoCalibrationMode.SUM,
    calibration_offset=-14.4,
)
```

**With context manager**:

```python
pwm_cfg = PWMDriverConfig(
    name=SunfounderPWM.DRIVER_TYPE,  # or "Sunfounder"
    address=0x14,                    # 0x14, 0x15 or 0x16
    bus=1,
    frame_width=20000,
    freq=50,
)

with PWMFactory.create_pwm_driver(pwm_cfg) as driver:
    hw = Servo(driver=driver, channel="P2")
    driver.set_pwm_freq(pwm_cfg.freq)
    steering_servo = ServoService(
        name="steering",
        servo=hw,
        min_angle=-30,
        max_angle=30,
        calibration_mode=ServoCalibrationMode.SUM,
        calibration_offset=-14.4,
    )
    steering_servo.set_angle(-30.0)
    steering_servo.set_angle(15.0)
    steering_servo.reset()
```

> [!NOTE]
>
> - Sunfounder devices typically use one of these addresses: 0x14, 0x15, 0x16. Pick the address that matches your hardware.
> - `ServoService` has a new `reverse` flag. Set `reverse=True` to mirror angles when mechanical linkage is inverted.

**Using PCA9685 (example)**:

```python
from robot_hat import PWMDriverConfig, PWMFactory, Servo, PCA9685

pwm_cfg = PWMDriverConfig(
    name="PCA9685",
    address=0x40,
    bus=1,
    frame_width=20000,
    freq=50,
)

with PWMFactory.create_pwm_driver(pwm_cfg) as driver:
    driver.set_pwm_freq(pwm_cfg.freq)
    servo = Servo(driver=driver, channel=0)
    servo.angle(0.0)
```

**Legacy Sunfounder-style servo (kept for compatibility)**:

```python
from robot_hat import ServoService, ServoCalibrationMode
from robot_hat.sunfounder.sunfounder_servo import Servo as SunfounderServo

steering_servo = ServoService(
    name="steering",
    servo=SunfounderServo("P1"),
    min_angle=-30,
    max_angle=30,
    calibration_mode=ServoCalibrationMode.SUM,
    calibration_offset=-14.4,
)
steering_servo.set_angle(-30.0)
steering_servo.set_angle(15.0)
steering_servo.reset()
```

# Motors

Old code used `MotorConfig` and `MotorFabric`. These are replaced by dataclass configs and `MotorFactory`.

**Old:**

```python
from robot_hat import MotorConfig, MotorService, MotorFabric

left_motor, right_motor = MotorFabric.create_motor_pair(
    MotorConfig(
        dir_pin="D4",
        pwm_pin="P12",
        name="LeftMotor",
    ),
    MotorConfig(
        dir_pin="D5",
        pwm_pin="P13",
        name="RightMotor",
    ),
)
motor_service = MotorService(left_motor=left_motor, right_motor=right_motor)
```

**New (recommended approach)**:

```python
from robot_hat import (
    I2CDCMotorConfig,
    MotorFactory,
    MotorService,
    PWMDriverConfig,
    PWMFactory,
    SunfounderPWM,
)

driver_cfg = PWMDriverConfig(
    name=SunfounderPWM.DRIVER_TYPE, bus=1, frame_width=20000, freq=50, address=0x14
)

driver = PWMFactory.create_pwm_driver(driver_cfg, bus=1)

motor_service = MotorService(
    left_motor=MotorFactory.create_motor(
        config=I2CDCMotorConfig(
            calibration_direction=1,
            name="left_motor",
            max_speed=100,
            driver=driver_cfg,
            channel="P12",
            dir_pin="D4",
        ),
        driver=driver,
    ),
    right_motor=MotorFactory.create_motor(
        config=I2CDCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            driver=driver_cfg,
            channel="P13",
            dir_pin="D5",
        ),
        driver=driver,
    ),
)
```

> [!NOTE]
> Sunfounder PWM devices typically use addresses 0x14, 0x15, or 0x16.
> Choose the one that matches your hardware.
> `MotorService.move(speed, direction)` now also accepts `direction=0` to stop both motors.

**Legacy Sunfounder-style motor (kept for compatibility)**:

```python
from robot_hat import MotorService, Pin
from robot_hat.sunfounder import PWM, Motor

left_motor = Motor(dir_pin=Pin("D4"), pwm_pin=PWM("P12"), name="LeftMotor")
right_motor = Motor(dir_pin=Pin("D5"), pwm_pin=PWM("P13"), name="RightMotor")
motor_service = MotorService(left_motor=left_motor, right_motor=right_motor)
```

# Batteries

Two batteries are available:

- Sunfounder ADC-based battery (legacy-compatible)
- INA219 I2C battery (Waveshare UPS and similar)

**Sunfounder ADC battery (compat path)**:

```python
from robot_hat.services.battery.sunfounder_battery import Battery as SunfounderBattery

battery = SunfounderBattery(channel="A4")
print(battery.get_battery_voltage())
```

Or top-level alias:

```python
from robot_hat import SunfounderBattery
```

**INA219 battery (recommended for INA219-based stacks)**:

```python
from robot_hat import INA219Battery

battery = INA219Battery(bus=1, address=0x41)
print(battery.get_battery_voltage())
```

> [!NOTE]
> For fine control of INA219 scaling and range, build and pass an `INA219Config`
> (e.g., `INA219Config.from_shunt(...)`).

## Common pitfalls and tips

- Sunfounder servos now expect float angles. If you previously passed ints, convert: `servo.set_angle(15.0)`.
- `ServoService` no longer accepts `servo_pin`; pass a servo object that implements `ServoABC`.
- Because calibration now applies after constraining, steering/neutral points may shift. Re-tune `calibration_offset`.
- `ServoService` has a new `reverse=True` option to mirror angles when your linkage is physically reversed.
- `MotorService.move(..., direction=0)` explicitly stops both motors.
- `Pin(int)` now accepts any GPIO name/number that gpiozero can resolve. If your code relied on `InvalidPinNumber` for integer validation
