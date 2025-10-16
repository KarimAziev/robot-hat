[![PyPI](https://img.shields.io/pypi/v/robot-hat)](https://pypi.org/project/robot-hat/)
[![codecov](https://codecov.io/gh/KarimAziev/robot-hat/graph/badge.svg?token=2C863KHRLU)](https://codecov.io/gh/KarimAziev/robot-hat)

> ⚠️ Breaking changes in v2.0.0 - This release contains incompatible API changes. Read the [CHANGELOG](https://github.com/KarimAziev/robot-hat/blob/main/CHANGELOG.md) and the [Migration Guide](https://github.com/KarimAziev/robot-hat/blob/v2.0.0/docs/migration_guide_v2.md) before upgrading.

# Robot Hat

This is a Python library for controlling hardware peripherals commonly used in robotics. This library provides APIs for controlling **motors**, **servos**, **ultrasonic sensors**, **analog-to-digital converters (ADCs)**, and more, with a focus on extensibility, ease of use, and modern Python practices.

The motivation comes from dissatisfaction with the code quality, safety, and unnecessary sudo requirements found in many mainstream libraries provided by well-known robotics suppliers, such as [Sunfounder's Robot-HAT](https://github.com/sunfounder/robot-hat/tree/v2.0) or [Freenove's Pidog](https://github.com/Freenove/Freenove_Robot_Dog_Kit_for_Raspberry_Pi).

Another reason is to provide a unified way to use different servo and motor controllers without writing custom code (or copying untyped, poorly written examples) for every hardware vendor.

Originally written as a replacement for Sunfounder's Robot-HAT, this library now also supports other peripherals and allows users to register custom drivers.

Unlike the aforementioned libraries:

- This library scales well for **both small and large robotics projects**. For example, advanced usage is demonstrated in the [Picar-X Racer](https://github.com/KarimAziev/picar-x-racer) project.
- It offers type safety and portability.
- It avoids requiring **sudo calls** or introducing unnecessary system dependencies, focusing instead on clean, self-contained operations.
- Plugin-style extensibility.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Robot Hat](#robot-hat)
>   - [Installation](#installation)
>   - [Usage examples](#usage-examples)
>     - [Motor control](#motor-control)
>     - [GPIO-driven DC motors](#gpio-driven-dc-motors)
>     - [I2C-driven DC motors](#i2c-driven-dc-motors)
>     - [Controlling a servo motor with ServoCalibrationMode](#controlling-a-servo-motor-with-servocalibrationmode)
>     - [Shared I2C bus instance](#shared-i2c-bus-instance)
>     - [Combined example with vehicle robot (shared bus instance, servos and motors)](#combined-example-with-vehicle-robot-shared-bus-instance-servos-and-motors)
>     - [I2C example](#i2c-example)
>     - [GPIO Pin](#gpio-pin)
>     - [Ultrasonic sensor for distance measurement](#ultrasonic-sensor-for-distance-measurement)
>     - [Reading battery voltage](#reading-battery-voltage)
>       - [INA219](#ina219)
>       - [INA226](#ina226)
>       - [INA260](#ina260)
>       - [Sunfounder module](#sunfounder-module)
>       - [Battery Factory](#battery-factory)
>   - [Adding custom drivers](#adding-custom-drivers)
>     - [How to make your driver discoverable](#how-to-make-your-driver-discoverable)
>   - [Comparison with Other Libraries](#comparison-with-other-libraries)
>     - [No sudo](#no-sudo)
>     - [Type Hints](#type-hints)
>     - [Mock Support for Testing](#mock-support-for-testing)
>   - [Development Environment Setup](#development-environment-setup)
>     - [Prerequisites](#prerequisites)
>     - [Steps to Set Up](#steps-to-set-up)
>   - [Distribution](#distribution)
>   - [Common Commands](#common-commands)
>   - [Notes & Recommendations](#notes--recommendations)

<!-- markdown-toc end -->

## Installation

Install this package via `pip` or your preferred package manager:

```bash
pip install robot-hat
```

## Usage examples

### Motor control

Three types of motors are currently supported: GPIO-driven motors, phase motors, and I2C DC motors. All are controlled the same way using `MotorService` modules.

### GPIO-driven DC motors

GPIO motors are motors that are controlled entirely via direct GPIO calls; no I²C address or external PWM driver is needed. Examples include the Waveshare RPi Motor Driver Board with the MC33886 module.

```python
from robot_hat import GPIODCMotorConfig, MotorFactory, MotorService, setup_env_vars

setup_env_vars() # autosetup environment, e.g.: GPIOZERO_PIN_FACTORY, ROBOT_HAT_MOCK_SMBUS etc

left_motor = MotorFactory.create_motor(
    config=GPIODCMotorConfig(
        calibration_direction=1,
        name="left_motor",
        max_speed=100,
        forward_pin=6,
        backward_pin=13,
        enable_pin=12,
        pwm=True,
    )
)
right_motor = MotorFactory.create_motor(
    config=GPIODCMotorConfig(
        calibration_direction=1,
        name="right_motor",
        max_speed=100,
        forward_pin=20,
        backward_pin=21,
        pwm=True,
        enable_pin=26,
    )
)

speed = 40
motor_service.move(speed, 1)
# increase speed
motor_service.move(motor_service.speed + 10, 1)

# move backward
motor_service.move(speed, -1)

# stop
motor_service.stop_all()

```

### I2C-driven DC motors

I2C-driven motors rely on an external PWM driver (e.g., PCA9685, Sunfounder) to control motor speed via I²C.

```python
from robot_hat import (
    I2CDCMotorConfig,
    MotorFactory,
    MotorService,
    PWMDriverConfig,
    PWMFactory,
)

setup_env_vars() # autosetup environment, e.g.: GPIOZERO_PIN_FACTORY, ROBOT_HAT_MOCK_SMBUS etc

driver_cfg = PWMDriverConfig(
    name="Sunfounder",  # 'PCA9685', 'Sunfounder', or a custom driver.
    bus=1,
    frame_width=20000,
    freq=50,
    address=0x14,
)
driver = PWMFactory.create_pwm_driver(driver_cfg, bus=1)

motor_service = MotorService(
    left_motor=MotorFactory.create_motor(
        config=I2CDCMotorConfig(
            calibration_direction=1,
            name="left_motor",
            max_speed=100,
            driver=driver_cfg,
            channel="P12",  # Either an integer or a string with a numeric suffix.
            dir_pin="D4",  # Digital output pin used to control the motor's direction.
        ),
        driver=driver,
    ),
    right_motor=MotorFactory.create_motor(
        config=I2CDCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            driver=driver_cfg,
            channel="P13",  # Either an integer or a string with a numeric suffix.
            dir_pin="D5",  # Digital output pin used to control the motor's direction.
        ),
        driver=driver,
    ),
)
```

### Controlling a servo motor with ServoCalibrationMode

The `ServoCalibrationMode` enum defines how calibration offsets are applied to a servo's angle. It supports two predefined modes and also allows custom calibration functions for advanced use cases.

Available modes

- **SUM**: Adds a constant offset (`calibration_offset`) to the input angle. This is generally used for steering operations, such as controlling the front wheels of a robotic car.

Formula:

```
calibrated_angle = input_angle + calibration_offset
```

- **NEGATIVE**: Applies an inverted adjustment combined with an offset. This mode may be helpful for servos that require an inverted calibration, such as a camera tilt mechanism.
  Formula:

```python-console
calibrated_angle = -1 × (input_angle + (-1 × calibration_offset))
```

**Configuring the `ServoService`**

The `ServoService` provides a high-level abstraction for managing servo operations. It allows easy configuration of the calibration mode, movement bounds, and custom calibration logic if needed.

Here's how to use `ServoCalibrationMode` in your servo configuration:

**Example 1**: Steering servo using `ServoCalibrationMode.SUM`

For steering purposes (e.g., controlling the front wheels of a robotic car):

```python
from robot_hat import (
    PWMDriverConfig,
    PWMFactory,
    Servo,
    ServoCalibrationMode,
    ServoService,
    setup_env_vars,
)

setup_env_vars()  # autosetup environment, e.g.: GPIOZERO_PIN_FACTORY, ROBOT_HAT_MOCK_SMBUS etc


pwm_config = PWMDriverConfig(
    name="PCA9685",  # 'PCA9685' or 'Sunfounder', or register a custom driver.
    address=0x40,  # I2C address of the device
    bus=1,  # The I2C bus number used to communicate with the PWM driver chip
    # The parameters below are optional and have default values:
    frame_width=20000,
    freq=50,
)
driver = PWMFactory.create_pwm_driver(
    bus=pwm_config.bus,  # either a bus number or an smbus instance.
    config=pwm_config,
)

steering_servo = ServoService(
    servo=Servo(
        driver=driver,
        channel="P1",  # Either an integer or a string with a numeric suffix.
        # The parameters below are optional and have default values:
        # The minimum and maximum logical angles (in degrees) that can be commanded to the servo.
        min_angle=-90.0,
        max_angle=90.0,
        # The minimum and maximum pulse widths (in microseconds) corresponding to the servo's physical movement.
        min_pulse=500,
        max_pulse=2500,
        # The minimum and maximum physical angles (in degrees) that the servo can achieve.
        # These values are used to map the logical angle to the physical angle.
        real_min_angle=-90.0,
        real_max_angle=90.0,
    ),
    name="steering",  # A human-readable name for the servo (useful for debugging/logging).
    min_angle=-90,
    max_angle=90,
    calibration_mode=ServoCalibrationMode.SUM,
    calibration_offset=-14.4,
)
driver.set_pwm_freq(pwm_config.freq)

steering_servo.set_angle(-30)  # Turn left.
steering_servo.set_angle(15)  # Turn slightly to the right.
steering_servo.reset()  # Reset to the center position.

# Calibration
print(steering_servo.calibration_offset)  # -14.4
steering_servo.update_calibration(
    -10.2
)  # temporarly update calibration until reset_calibration is called
print(steering_servo.calibration_offset)  # -10.2
steering_servo.reset_calibration()
print(steering_servo.calibration_offset)  # -14.4
steering_servo.update_calibration(-1.5, persist=True)
print(steering_servo.calibration_offset)  # -1.5
steering_servo.reset_calibration()  # resets to persisted value
print(steering_servo.calibration_offset)  # -1.5

steering_servo.close()  # Close and clean up the servo.

```

**Example 2**: Head servos using `ServoCalibrationMode.NEGATIVE`

For tilting a camera head (e.g., up-and-down movement):

```python
cam_tilt_servo = ServoService(
    name="tilt",
    servo=Servo(
        driver=driver,
        channel="P1",  # Either an integer or a string with a numeric suffix.
    ),
    min_angle=-35,  # Maximum downward tilt
    max_angle=65,  # Maximum upward tilt
    calibration_mode=ServoCalibrationMode.NEGATIVE,  # Inverted adjustment
    calibration_offset=1.4,  # Adjust alignment for neutral center
)

driver.set_pwm_freq(pwm_config.freq)

cam_tilt_servo.set_angle(-20)  # Tilt down
cam_tilt_servo.set_angle(25)  # Tilt up
cam_tilt_servo.reset()  # Center position
```

**Example 3**: Custom calibration mode

If the predefined modes (`SUM` or `NEGATIVE`) don’t meet your requirements, you can provide a custom calibration function. The function should accept `angle` and `calibration_offset` as inputs and return the calibrated angle.

```python
def custom_calibration_function(angle: float, offset: float) -> float:
    """Scale angle by 2 and add offset to fine-tune servo position."""
    return (angle * 2) + offset


cam_tilt_servo = ServoService(
    name="tilt",
    servo=Servo(
        driver=driver,
        channel="P1",  # Either an integer or a string with a numeric suffix.
    ),
    min_angle=-35,  # Maximum downward tilt
    max_angle=65,  # Maximum upward tilt
    calibration_mode=custom_calibration_function,
    calibration_offset=1.4,  # Adjust alignment for neutral center
)

cam_tilt_servo.set_angle(10)  # Custom logic will process the input angle
```

### Shared I2C bus instance

Share I2C buses via SMBusManager where possible to avoid device contention and duplicated resources. SMBusManager.get_bus(n) returns the same bus instance for the same bus number, so multiple callers will get a single shared object:

```python
from robot_hat import SMBusManager

bus0 = SMBusManager.get_bus(0)
bus1 = SMBusManager.get_bus(1)
bus0_again = SMBusManager.get_bus(0)

print(bus0 is bus0_again)  # True
```

You can explicitly close a bus or all buses when your program is shutting down:

```python
SMBusManager.close_bus(0)   # close bus 0
SMBusManager.close_all()    # close all managed buses
```

Most classes that accept a bus parameter will accept either a bus number or a bus instance. Prefer passing the shared bus instance to ensure all devices use the same underlying SMBus:

```python
from robot_hat import SMBusManager, PWMFactory, I2C

shared_bus = SMBusManager.get_bus(1)

pwm_driver = PWMFactory.create_pwm_driver(
    bus=shared_bus,
    config=pwm_config,
)

i2c_device = I2C(address=[0x15, 0x17], bus=shared_bus)
```

Note: only one underlying bus instance is created per bus number (in the example above, bus 1 is created once and reused).

> [!IMPORTANT]
> Don't call `SMBusManager.close_bus(...)` while other components still expect the bus to be open. Before calling `SMBusManager.close_bus(...)` or `SMBusManager.close_all()`, make sure all device objects are stopped/closed or otherwise no longer accessing the bus.

### Combined example with vehicle robot (shared bus instance, servos and motors)

This example shows how to share a single I²C/SMBus instance across multiple drivers and devices (servos, PWM controllers, sensors, etc.) in a robot application.

Instead of letting each driver open its own `SMBus`, the example uses `SMBusManager` to create or reuse a single I2CBus object and pass it into PWM/motor/ADC drivers. Sharing the bus avoids duplicate opens, file-descriptor leaks, and inconsistent behavior when multiple parts of your program talk to devices on the same physical I²C bus.

<details><summary>Show example</summary>
<p>

```python
import logging
from typing import Callable, Dict, Optional, Union

from robot_hat import (
    GPIOAngularServo,
    GPIODCMotorConfig,
    MotorABC,
    MotorConfigType,
    MotorFactory,
    MotorService,
    MotorServiceDirection,
    PWMDriverConfig,
    PWMFactory,
    Servo,
    ServoCalibrationMode,
    ServoService,
    SMBusManager,
)

_log = logging.getLogger(__name__)


class MyRobotCar:
    def __init__(
        self,
        pwm_config: Optional[PWMDriverConfig] = None,
        pan_servo_channel: Union[int, str] = "P0",
        tilt_servo_channel: Union[int, str] = "P1",
        steering_servo_channel: Union[int, str] = "P2",
        left_motor_config: Optional[MotorConfigType] = None,
        right_motor_config: Optional[MotorConfigType] = None,
    ) -> None:

        self.smbus_manager = SMBusManager()

        self.left_motor: Optional[MotorABC] = None
        self.right_motor: Optional[MotorABC] = None
        self.cam_pan_servo: Optional[ServoService] = None
        self.cam_tilt_servo: Optional[ServoService] = None
        self.steering_servo: Optional[ServoService] = None

        self.setup(
            pwm_config=pwm_config,
            pan_servo_channel=pan_servo_channel,
            tilt_servo_channel=tilt_servo_channel,
            steering_servo_channel=steering_servo_channel,
            left_motor_config=left_motor_config,
            right_motor_config=right_motor_config,
        )

    def setup(
        self,
        pwm_config: Optional[PWMDriverConfig],
        pan_servo_channel: Union[int, str],
        tilt_servo_channel: Union[int, str],
        steering_servo_channel: Union[int, str],
        left_motor_config: Optional[MotorConfigType],
        right_motor_config: Optional[MotorConfigType],
    ):
        self._setup_servo(
            pwm_config=pwm_config,
            pan_servo_channel=pan_servo_channel,
            tilt_servo_channel=tilt_servo_channel,
            steering_servo_channel=steering_servo_channel,
        )

        self._setup_motors(
            left_motor_config=left_motor_config, right_motor_config=right_motor_config
        )

    def _setup_servo(
        self,
        pwm_config: Optional[PWMDriverConfig],
        pan_servo_channel: Union[int, str],
        tilt_servo_channel: Union[int, str],
        steering_servo_channel: Union[int, str],
    ) -> None:
        self.cam_pan_servo = self._make_servo(
            name="cam_pan", pwm_config=pwm_config, channel=pan_servo_channel
        )
        self.cam_tilt_servo = self._make_servo(
            name="cam_tilt", pwm_config=pwm_config, channel=tilt_servo_channel
        )
        self.steering_servo = self._make_servo(
            name="steering", pwm_config=pwm_config, channel=steering_servo_channel
        )

    def _setup_motors(
        self,
        left_motor_config: Optional[MotorConfigType],
        right_motor_config: Optional[MotorConfigType],
    ) -> None:
        if left_motor_config and right_motor_config:
            self.left_motor = MotorFactory.create_motor(config=left_motor_config)
            self.right_motor = MotorFactory.create_motor(config=right_motor_config)
            self.motor_controller = MotorService(
                left_motor=self.left_motor, right_motor=self.right_motor
            )

    def _make_servo(
        self,
        channel: Union[int, str],
        name: str,
        min_angle=-90,
        max_angle=90,
        calibration_offset=0.0,
        reverse: bool = False,
        pwm_config: Optional[PWMDriverConfig] = None,
        calibration_mode: Optional[
            Union[ServoCalibrationMode, Callable[[float, float], float]]
        ] = ServoCalibrationMode.SUM,
    ) -> ServoService:
        if pwm_config is not None:
            driver = PWMFactory.create_pwm_driver(
                bus=self.smbus_manager.get_bus(pwm_config.bus),
                config=pwm_config,
            )

            servo = Servo(
                channel=channel,
                driver=driver,
            )
            driver.set_pwm_freq(pwm_config.freq)

        else:
            servo = GPIOAngularServo(
                pin=channel,
                min_angle=min_angle,
                max_angle=max_angle,
            )
        return ServoService(
            servo=servo,
            calibration_offset=calibration_offset,
            min_angle=min_angle,
            max_angle=max_angle,
            calibration_mode=calibration_mode,
            name=name,
            reverse=reverse,
        )

    def move(self, speed: int, direction: MotorServiceDirection) -> None:
        """
        Move the robot forward or backward.

        Args:
        - speed: The base speed at which to move.
        - direction: 1 for forward, -1 for backward, 0 for stop.
        """
        self.motor_controller.move(speed, direction)

    @property
    def state(self) -> Dict[str, float]:
        """
        Returns key metrics of the current state as a dictionary.
        """
        return {
            "speed": self.motor_controller.speed if self.motor_controller else 0,
            "direction": (
                self.motor_controller.direction if self.motor_controller else 0
            ),
            "steering_servo_angle": (
                self.steering_servo.current_angle if self.steering_servo else 0
            ),
            "cam_pan_angle": (
                self.cam_pan_servo.current_angle if self.cam_pan_servo else 0
            ),
            "cam_tilt_angle": (
                self.cam_tilt_servo.current_angle if self.cam_tilt_servo else 0
            ),
        }

    def stop(self) -> None:
        """
        Stop the motors.
        """
        return self.motor_controller.stop_all()

    def cleanup(self):
        """
        Clean up hardware resources by stopping all motors and gracefully closing all
        associated I2C connections for both motors and servos.
        """

        if self.motor_controller:
            try:
                self.stop()
                self.motor_controller.close()
            except (TimeoutError, OSError) as e:
                err_msg = str(e)
                _log.error(err_msg)
            except Exception as e:
                _log.error(
                    "Unexpected error while closing motor controller %s",
                    e,
                    exc_info=True,
                )
        else:
            for motor in [self.left_motor, self.right_motor]:
                if motor:
                    try:
                        motor.close()
                    except Exception as e:
                        _log.error("Error closing motor %s", e)

        self.right_motor = None
        self.left_motor = None

        for servo_service in [
            self.steering_servo,
            self.cam_tilt_servo,
            self.cam_pan_servo,
        ]:
            if servo_service:
                try:
                    servo_service.close()
                except (TimeoutError, OSError) as e:
                    err_msg = str(e)
                    _log.error(err_msg)
                except Exception as e:
                    _log.error("Error closing servo %s", e)


if __name__ == "__main__":
    from robot_hat.utils import setup_env_vars

    setup_env_vars()
    robot_car = MyRobotCar(
        left_motor_config=GPIODCMotorConfig(
            calibration_direction=1,
            name="left_motor",
            max_speed=100,
            forward_pin=6,
            backward_pin=13,
            enable_pin=12,
            pwm=True,
        ),
        right_motor_config=GPIODCMotorConfig(
            calibration_direction=1,
            name="right_motor",
            max_speed=100,
            forward_pin=20,
            backward_pin=21,
            enable_pin=26,
            pwm=True,
        ),
        pwm_config=PWMDriverConfig(
            name="PCA9685",
            address=0x40,
            bus=1,
        ),
    )
    robot_car.move(50, 1)
    robot_car.stop()
    robot_car.cleanup()

```

</p>
</details>

### I2C example

Scan and communicate with connected I2C devices.

```python
from robot_hat import I2C

# Initialize I2C connection
i2c_device = I2C(address=[0x15, 0x17], bus=1)

# Write a byte to the device
i2c_device.write(0x01)

# Read data from the device
data = i2c_device.read(5)
print("I2C Data Read:", data)

# Scan for connected devices
devices = i2c_device.scan()
print("I2C Devices Detected:", devices)

```

### GPIO Pin

The `Pin` class wraps gpiozero Input/Output devices and accepts either a GPIO pin number (int) or a string name.

When a string is passed, it must be either:

- a name recognized by gpiozero's pin factory (for example "GPIO17", "BCM17", physical/BOARD names such as "BOARD11", header notation such as "J8:11", or wiringPi names such as "WPI0")
- a name from a custom mapping. By default, Sunfounder's labels ("D0", "D1", ...) are used.

You can also provide your custom mapping via the `pin_dict` parameter. `pin_dict` must be a dict that maps string names to GPIO numbers.

> [!TIP]
> For testing on non-Raspberry Pi hosts, set the gpiozero pin factory to "mock" (e.g. via setup_env_vars() or by setting environment variable `GPIOZERO_PIN_FACTORY=mock`) so the examples can run without real hardware.

**Basic example**

```python
from robot_hat import Pin, setup_env_vars

setup_env_vars()  # optional: set GPIOZERO_PIN_FACTORY, etc

# Create a pin using GPIO number
led = Pin(17, mode=Pin.OUT)

# Turn on / off
led.on()
led.off()

# Alias methods
led.high()
led.low()

# Set value using call/operator syntax
led(1)   # set high (returns 1)
led(0)   # set low  (returns 0)

# Read back (this will switch the pin to input mode internally)
value = led.value()
print("Pin value:", value)

# Clean up when done
led.close()
```

> [!NOTE]
> If you call `value()` with no argument, and the current mode is None or OUT, Pin will switch to IN mode before reading.
> Calling value(0) or value(1) will ensure the pin is in OUT mode before setting it.

**Initialize from a named mapping or gpiozero names**

```python
from robot_hat import Pin

# Using the Sunfounder's mapping (e.g., "D0" -> GPIO17)
pin_d0 = Pin("D0", mode=Pin.OUT)
pin_d0.on()

# Using gpiozero-style names (resolved by the pin factory)
pin_by_name = Pin("GPIO27")     # or "BCM27", "BOARD13", "J8:13"
print(pin_by_name.name())       # -> e.g., "GPIO27"
```

**Input with internal pull-up/pull-down, and read value**

```python
from robot_hat import Pin

# Configure as input with internal pull-up resistor
button = Pin("GPIO27", mode=Pin.IN, pull=Pin.PULL_UP)

# Read current state (returns 0 or 1)
state = button.value()
print("Button pressed?" , bool(state))

# The library will create an InputDevice under the hood
button.close()
```

**Interrupts (irq) with debounce and pull configuration**

```python
from robot_hat import Pin
import time

def on_pressed():
    print("Pressed!")

def on_released():
    print("Released!")

sw = Pin("D1")  # mapping or gpiozero name
# Attach interrupt on both rising and falling edges, 200 ms debounce, enable pull-up
sw.irq(handler=on_pressed, trigger=Pin.IRQ_RISING_FALLING, bouncetime=200, pull=Pin.PULL_UP)

# Keep running to allow callbacks to run
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    sw.close()
```

**Custom named mapping**

```python
from robot_hat import Pin

# Provide your own name -> gpio mapping
my_mapping = {"MOTOR_EN": 12, "MOTOR_DIR": 20}
motor_en = Pin("MOTOR_EN", mode=Pin.OUT, pin_dict=my_mapping)
motor_en.on()
motor_en.close()
```

### Ultrasonic sensor for distance measurement

Measure distance using the `HC-SR04` ultrasonic sensor module.

```python
from robot_hat import Pin, Ultrasonic

# Initialize Ultrasonic Sensor
trig_pin = Pin("GPIO27")  # or integer or other pin mapping
echo_pin = Pin(17)  # or string or other pin mapping
ultrasonic = Ultrasonic(trig_pin, echo_pin)

# Measure distance
distance_cm = ultrasonic.read(times=5)
print(f"Distance: {distance_cm} cm")

```

### Reading battery voltage

Currently, such battery drivers are supported: **INA219**, **INA226** and the built-in driver in Sunfounder's Robot Hat.

#### INA219

Simple example with **INA219** (tested on Waveshare UPS Module 3S)

```python
from robot_hat import INA219Battery

battery = INA219Battery(address=0x41, bus=1)
```

**More about custom INA219 configuration**

The INA219 requires a calibration that depends on your shunt resistor and the maximum current you expect to measure. The library exposes `INA219Config` and a helper constructor `INA219Config.from_shunt(shunt_res_ohms, max_expected_current_a, ...)`, which:

- selects a sensible PGA gain for the expected shunt voltage,
- computes the Current_LSB and CAL register value,
- derives the Power_LSB (per datasheet: 20 × Current_LSB),
- allows tuning ADC averaging/resolution and the device operating mode.

Key points / units

- `shunt_res_ohms`: Ohms of the external shunt resistor (must be > 0).
- `max_expected_current_a`: maximum expected current in amperes (> 0).
- `current_lsb` returned in the config is in mA per bit (the dataclass stores it in mA units).
- `calibration_value` is the 16-bit calibration register written to the device.
- `power_lsb` is in W per bit.
- `from_shunt()` will raise `ValueError` if the expected shunt voltage exceeds the INA219's 320 mV limit.

<details><summary>Show example with custom INA219 config</summary>

**Example**: configure INA219 for a 0.01 Ω shunt and up to 5 A expected current

<p>

```python
from robot_hat import INA219Battery
from robot_hat.data_types.config.ina219 import (
    ADCResolution,
    BusVoltageRange,
    INA219Config,
    Mode,
)
 # Build a configuration from your shunt resistor and expected max current.
 # Here: R_shunt = 0.01 Ω, I_max = 5 A => V_shunt_max = 0.05 V (50 mV), fits within INA219 ranges.

custom_cfg = INA219Config.from_shunt(
    shunt_res_ohms=0.01,  # 10 milliohm shunt
    max_expected_current_a=5.0,  # up to 5 A
    bus_voltage_range=BusVoltageRange.RANGE_32V,  # defaults to 32V range (optional)
    bus_adc_resolution=ADCResolution.ADCRES_12BIT_128S,  # high averaging for noise suppression
    shunt_adc_resolution=ADCResolution.ADCRES_12BIT_128S,  # same for shunt ADC
    mode=Mode.SHUNT_AND_BUS_CONTINUOUS,  # continuous shunt + bus measurement
    nice_current_lsb_step_mA=0.1,  # round Current_LSB up to 0.1 mA/bit steps (optional)
)

# Inspect derived values (helpful for diagnostics)
print("Derived INA219 config:", custom_cfg)
# current_lsb is stored in mA/bit in the dataclass:
print("Current LSB (mA/bit):", custom_cfg.current_lsb)
print("Calibration register value:", custom_cfg.calibration_value)
print("Power LSB (W/bit):", custom_cfg.power_lsb)

# Create Battery instance with custom configuration
battery = INA219Battery(address=0x41, bus=1, config=custom_cfg)

# Read values
bus_v = battery.get_bus_voltage_v()  # bus voltage (V)
shunt_mv = battery.get_shunt_voltage_mv()  # shunt voltage (mV)
battery_v = battery.get_battery_voltage()  # bus + shunt (V)
current_ma = battery.get_current_ma()  # current (mA)
power_w = battery.get_power_w()  # power (W)

print(f"Bus: {bus_v:.3f} V, Shunt: {shunt_mv:.3f} mV")
print(f"Battery (bus + shunt): {battery_v:.3f} V")
print(f"Current: {current_ma:.3f} mA, Power: {power_w:.3f} W")

# If you need to change calibration / averaging at runtime:
new_cfg = INA219Config.from_shunt(
    shunt_res_ohms=0.01,
    max_expected_current_a=3.0,  # lower I_max -> different calibration
    bus_adc_resolution=ADCResolution.ADCRES_12BIT_32S,
    shunt_adc_resolution=ADCResolution.ADCRES_12BIT_32S,
)
battery.update_config(new_cfg)  # writes new CAL and CONFIG registers

# Close when finished (closes bus if driver opened it)
battery.close()

```

</p>
</details>

#### INA226

The INA226 driver in this library exposes a config dataclass (`INA226Config`) and a driver (`INA226`). A small Battery helper (`robot_hat.services.battery.ina226_battery.Battery`) wraps the driver to provide a battery-focused API (get_battery_voltage, close).

**Simple example**

```python
from robot_hat.services.battery.ina226_battery import Battery as INA226Battery
from robot_hat.data_types.config.ina226 import INA226Config

# Build a config derived from your shunt resistor and max expected current.
# shunt_ohms must be > 0. max_expected_amps is optional (if omitted the code uses a
# device-limited derivation).
cfg = INA226Config.from_shunt(
    shunt_ohms=0.002,           # 2 milliohm shunt
    max_expected_amps=50.0      # expected up to 50 A (example)
)

# Create Battery helper (driver opens SMBus if you pass bus number)
battery = INA226Battery(bus=1, address=0x40, config=cfg)


bus_v = battery.get_bus_voltage_v()      # bus voltage in volts (V)
shunt_mv = battery.get_shunt_voltage_mv()# shunt voltage in millivolts (mV)
battery_v = battery.get_battery_voltage()# bus + shunt in volts (V)
current_ma = battery.get_current_ma()    # current in milliamps (mA)
power_mw = battery.get_power_mw()        # power in milliwatts (mW)

print(f"Bus: {bus_v:.3f} V, Shunt: {shunt_mv:.3f} mV")
print(f"Battery (bus + shunt): {battery_v:.3f} V")
print(f"Current: {current_ma:.3f} mA, Power: {power_mw:.3f} mW")

battery.close()
```

#### INA260

The INA260 variant integrates a fixed 2 mΩ shunt, so calibration values are part of the config defaults. The battery helper (`robot_hat.services.battery.ina260_battery.Battery`) combines bus voltage with the shunt drop to give the pack voltage, just like the INA219/INA226 helpers.

**Simple example**

```python
from robot_hat.services.battery.ina260_battery import Battery as INA260Battery
from robot_hat.data_types.config.ina260 import (
    AveragingCount,
    ConversionTime,
    INA260Config,
    Mode,
)

config = INA260Config(
    averaging_count=AveragingCount.COUNT_16,
    voltage_conversion_time=ConversionTime.TIME_1_1_MS,
    current_conversion_time=ConversionTime.TIME_1_1_MS,
    mode=Mode.CONTINUOUS,
)

battery = INA260Battery(bus=1, address=0x40, config=config)

bus_v = battery.get_bus_voltage_v()
shunt_mv = battery.get_shunt_voltage_mv()
battery_v = battery.get_battery_voltage()
current_ma = battery.get_current_ma()
power_mw = battery.get_power_mw()

print(f"Bus: {bus_v:.3f} V, Shunt: {shunt_mv:.3f} mV")
print(f"Battery: {battery_v:.2f} V, Current: {current_ma/1000:.3f} A")
print(f"Power: {power_mw/1000:.3f} W")

battery.close()
```

#### Sunfounder module

```python
from robot_hat import SunfounderBattery

battery = SunfounderBattery(channel="A4", address=[0x14, 0x15], bus=1)

voltage = battery.get_battery_voltage()  # Read battery voltage
print(f"Battery Voltage: {voltage} V")
```

#### Battery Factory

When you need to choose a battery helper dynamically, use the unified factory and
config dataclasses. Each helper has a matching config in
`robot_hat.data_types.config.battery`.

```python
from robot_hat import BatteryFactory, INA260BatteryConfig

battery = BatteryFactory.create_battery(
    INA260BatteryConfig(bus=1, address=0x40)
)

print(battery.get_battery_voltage())
```

The factory supports INA219, INA226, INA260, and the legacy Sunfounder helper via
`SunfounderBatteryConfig`.

## Adding custom drivers

This library uses a plugin-style registry for PWM drivers so you can add support for new hardware without changing core code.

The base class manages the I2C/SMBus instance when the constructor receives either an int (bus number) or a bus object. Implement the `PWMDriverABC` interface, give your driver a meaningful name that matches the config, and register it with `@register_pwm_driver`.

**Minimal example**

```python
import logging
from typing import Optional

from robot_hat import BusType, PWMDriverABC, register_pwm_driver

_log = logging.getLogger(__name__)


@register_pwm_driver
class MyDriver(PWMDriverABC):
    DRIVER_TYPE = "MyDriver"  # Must match PWMDriverConfig.name

    def __init__(
        self,
        address: int,
        bus: BusType = 1,
        frame_width: Optional[int] = 20000,
        **kwargs
    ) -> None:
        # Let the base class resolve or wrap the bus parameter
        super().__init__(bus=bus, address=address)
        self._frame_width = frame_width if frame_width is not None else 20000
        _log.debug("Initialized MyDriver at 0x%02X on bus %s", address, bus)

    def set_pwm_freq(self, freq: int) -> None:
        # implement frequency setup for your chip
        _log.debug("MyDriver.set_pwm_freq(%d)", freq)

    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        # convert pulse (µs) to whatever units your driver needs and write
        _log.debug("MyDriver.set_servo_pulse(channel=%d, pulse=%d)", channel, pulse)

    def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
        if not (0 <= duty <= 100):
            raise ValueError("Duty must be between 0 and 100")
        _log.debug("MyDriver.set_pwm_duty_cycle(channel=%d, duty=%d)", channel, duty)


if __name__ == "__main__":
    from robot_hat import PWMDriverConfig, PWMFactory, setup_env_vars

    setup_env_vars()
    pwm_config = PWMDriverConfig(
        name=MyDriver.DRIVER_TYPE,
        address=0x40,  # I2C address of the device
        bus=1,
    )

    my_driver = PWMFactory.create_pwm_driver(config=pwm_config)
    print(my_driver.DRIVER_TYPE)

```

Use it from config

```python
from robot_hat import PWMFactory, PWMDriverConfig
from .my_driver import MyDriver  # ensure your module is imported

pwm_config = PWMDriverConfig(
    name=MyDriver.DRIVER_TYPE,
    address=0x40,
    bus=1,
)

driver = PWMFactory.create_pwm_driver(config=pwm_config)
driver.set_pwm_freq(50)
```

### How to make your driver discoverable

Put the driver in your project and import it before calling `PWMFactory.create_pwm_driver`. The decorator registers it in the global registry.

Also, contributions are welcome but you don't have to upstream your driver - you can register and use custom drivers anywhere in your own code.

## Comparison with Other Libraries

### No sudo

For reasons that remain a mystery (and a source of endless frustration), the providers of many popular DRY robotics libraries insist on requiring `sudo` for the most basic operations. For example:

```python
User = os.popen('echo ${SUDO_USER:-$LOGNAME}').readline().strip()
UserHome = os.popen('getent passwd %s | cut -d: -f 6' % User).readline().strip()
config_file = '%s/.config/robot-hat/robot-hat.conf' % UserHome
```

And later, they modify file permissions with commands like:

```python
os.popen('sudo chmod %s %s' % (mode, file_path))  # 🤦
os.popen('sudo chown -R %s:%s %s' % (owner, owner, some_path))
```

This library removes all such archaic and potentially unsafe patterns by leveraging user-friendly Python APIs like `pathlib`. File-related operations are scoped to user-accessible directories (e.g., `~/.config`) rather than requiring administrative access
via `sudo`.

### Type Hints

This version prioritizes:

- **Type hints** for better developer experience.
- Modular, maintainable, and well-documented code.

### Mock Support for Testing

`Sunfounder` (and similar libraries) offer no direct way to mock their hardware APIs, making it nearly impossible to write meaningful unit tests on non-Raspberry Pi platforms.

This library can be configured either by environment values, either by function `setup_env_vars`, which will setup them automatically:

```python
from robot_hat.utils import setup_env_vars
setup_env_vars()
```

Or:

```python
import os
os.environ["GPIOZERO_PIN_FACTORY"] = "mock" # mock for non-raspberry pi, lgpio for Raspberry Pi 5 and rpigpio for other Raspberry versions
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
```

---

## Development Environment Setup

### Prerequisites

1. **Python 3.10 or newer** must be installed.
2. Ensure you have `pip` installed (a recent version is recommended):
   ```bash
   python3 -m pip install --upgrade pip
   ```

### Steps to Set Up

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/KarimAziev/robot-hat.git
   cd robot-hat
   ```

2. **Set Up a Virtual Environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # OR
   .venv\Scripts\activate     # Windows
   ```

3. **Upgrade Core Tools**:

   ```bash
   pip install --upgrade pip setuptools wheel
   ```

4. **Install in Development Mode**:
   ```bash
   pip install -e ".[dev]"  # Installs all dev dependencies (e.g., black, isort, pre-commit)
   ```

---

## Distribution

To create distributable artifacts (e.g., `.tar.gz` and `.whl` files):

1. Install the build tool:

   ```bash
   pip install build
   ```

2. Build the project:
   ```bash
   python -m build
   ```
   The built files will be located in the `dist/` directory:

- Source distribution: `robot_hat-x.y.z.tar.gz`
- Wheel: `robot_hat-x.y.z-py3-none-any.whl`

These can be installed locally for testing or uploaded to PyPI for distribution.

---

## Common Commands

- **Clean Build Artifacts**:
  ```bash
  rm -rf build dist *.egg-info
  ```
- **Deactivate Virtual Environment**:
  ```bash
  deactivate
  ```

---

## Notes & Recommendations

- The library uses `setuptools_scm` for versioning, which dynamically determines the version based on Git tags. Use proper semantic versioning (e.g., `v1.0.0`) in your repository for best results.
- Development tools like `black` (code formatter) and `isort` (import sorter) are automatically installed with `[dev]` dependencies.
