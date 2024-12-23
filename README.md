[![PyPI](https://img.shields.io/pypi/v/robot-hat)](https://pypi.org/project/robot-hat/)
[![codecov](https://codecov.io/gh/KarimAziev/robot-hat/graph/badge.svg?token=2C863KHRLU)](https://codecov.io/gh/KarimAziev/robot-hat)

# Robot Hat

This is a Python library for controlling hardware peripherals commonly used in robotics. This library provides APIs for controlling **motors**, **servos**, **ultrasonic sensors**, **analog-to-digital converters (ADCs)**, and more, with a focus on extensibility, ease of use, and modern Python practices.

The motivation comes from dissatisfaction with the code quality, safety, and unnecessary `sudo` requirements found in many mainstream libraries provided by well-known robotics suppliers, such as [Sunfounder's Robot-HAT](https://github.com/sunfounder/robot-hat/tree/v2.0) or [Freenove's Pidog](https://github.com/Freenove/Freenove_Robot_Dog_Kit_for_Raspberry_Pi). That being said, this library was originally written as a replacement for Sunfounder's Robot-HAT.

Unlike the aforementioned libraries:

- This library scales well for **both small and large robotics projects**. For example, advanced usage is demonstrated in the [Picar-X Racer](https://github.com/KarimAziev/picar-x-racer) project.
- It offers type safety and portability.
- It avoids requiring **sudo calls** or introducing unnecessary system dependencies, focusing instead on clean, self-contained operations.

<!-- markdown-toc start - Don't edit this section. Run M-x markdown-toc-refresh-toc -->

**Table of Contents**

> - [Robot Hat](#robot-hat)
>   - [Installation](#installation)
>   - [Usage Examples](#usage-examples)
>     - [Motor Control](#motor-control)
>     - [I2C Example](#i2c-example)
>     - [Ultrasonic Sensor for Distance Measurement](#ultrasonic-sensor-for-distance-measurement)
>     - [Reading Battery Voltage](#reading-battery-voltage)
>     - [Controlling a Servo Motor](#controlling-a-servo-motor)
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

Install this via `pip` or your favorite package manager:

```bash
pip install robot-hat
```

## Usage Examples

### Motor Control

Control dual motors using the `MotorController` modules.

```python
from robot_hat import MotorConfig, MotorController, MotorFabric

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
motor_controller = MotorController(left_motor=left_motor, right_motor=right_motor)

# move forward
speed = 40
motor_controller.move(speed, 1)

# move backward
motor_controller.move(speed, -1)

# stop
motor_controller.stop_all()

```

### I2C Example

Scan and communicate with connected I2C devices.

```python
from robot_hat.i2c import I2C

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

### Ultrasonic Sensor for Distance Measurement

Measure distance using the `HC-SR04` ultrasonic sensor module.

```python
from robot_hat.pin import Pin
from robot_hat.ultrasonic import Ultrasonic

# Initialize Ultrasonic Sensor
trig_pin = Pin("P9")
echo_pin = Pin("P10")
ultrasonic = Ultrasonic(trig_pin, echo_pin)

# Measure distance
distance_cm = ultrasonic.read(times=5)
print(f"Distance: {distance_cm} cm")
```

### Reading Battery Voltage

Use the ADC module to measure and scale the battery voltage.

```python
from robot_hat.battery import Battery

# Initialize Battery module
battery = Battery(channel="A4")

# Get battery voltage
voltage = battery.get_battery_voltage()
print(f"Battery Voltage: {voltage} V")
```

### Controlling a Servo Motor

Control the angle of a servo motor using PWM.

```python
from robot_hat.servo import Servo

# Initialize Servo motor
servo = Servo(channel="P0")

# Control servo angle
servo.angle(-90)  # Set angle to -90 degrees
servo.angle(45)   # Set angle to 45 degrees
servo.angle(0)    # Center position
```

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

```python
import os
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
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
