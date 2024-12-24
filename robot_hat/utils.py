import time
from functools import reduce
from typing import Callable, Tuple, TypeVar

T = TypeVar("T", int, float)


def compose(*functions: Callable) -> Callable:
    """
    Compose functions in reverse order (right-to-left).

    The output of one function is passed as the input to the next.
    The right-most function can accept any number of arguments.
    All subsequent functions should accept a single argument.

    Args:
        *functions: Functions to compose.

    Returns:
        A composed function that applies all the functions in sequence.

    Example:
    ```python
    def add(a, b):
        return a + b

    def double(x):
        return x * 2

    def to_string(x):
        return f"Result: {x}"

    # Compose functions
    composed = compose(to_string, double, add)
    result = composed(3, 7)  # add(3, 7) -> double(10) -> to_string(20)
    print(result)  # Output: "Result: 20"
    ```
    """

    if not functions:
        return lambda *args, **kwargs: args[0] if len(args) == 1 else args

    *rest, last = functions

    return lambda *args, **kwargs: reduce(
        lambda acc, func: func(acc),
        reversed(rest),
        last(*args, **kwargs),
    )


def run_command(cmd) -> Tuple[int | None, str]:
    """
    Run command and return status and output

    :param cmd: command to run
    :type cmd: str
    :return: status, output
    :rtype: tuple
    """
    import subprocess

    p = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )

    result = p.stdout.read().decode("utf-8") if p.stdout is not None else ""
    status = p.poll()
    return status, result


def reset_mcu_sync() -> None:
    """
    Resets the MCU (Microcontroller Unit) by toggling the state of the MCU reset pin.

    This function uses the robot hat adapter's Pin interface to manipulate the "MCURST"
    pin. The reset process is handled by briefly pulling the reset pin low (off),
    waiting for 10 milliseconds, and then pulling it high (on) again, followed by
    another short delay. Finally, the pin resource is released or closed.

    Steps:
      1. Instantiate the `MCURST` Pin object.
      2. Set the pin to the OFF state (low) to reset the MCU.
      3. Wait for 10 milliseconds.
      4. Set the pin to the ON state (high) to complete the reset.
      5. Wait for another 10 milliseconds.
      6. Close the Pin instance to release resources.

    This function is synchronous and blocks execution while the delays occur.

    Example:
      reset_mcu_sync()
    """
    from .pin import Pin

    mcu_reset = Pin("MCURST")
    mcu_reset.off()
    time.sleep(0.01)
    mcu_reset.on()
    time.sleep(0.01)

    mcu_reset.close()


def get_firmware_version() -> str:
    from .i2c import I2C

    ADDR = [0x14, 0x15]
    VERSSION_REG_ADDR = 0x05
    i2c = I2C(ADDR)
    version = i2c.mem_read(3, VERSSION_REG_ADDR)
    return f"{version[0]}.{version[1]}.{version[2]}"


def is_raspberry_pi() -> bool:
    """
    Check if the current operating system is running on a Raspberry Pi.

    Returns:
        bool: True if the OS is running on a Raspberry Pi, False otherwise.
    """
    try:
        with open("/proc/device-tree/model", "r") as file:
            model_info = file.read().lower()
        return "raspberry pi" in model_info
    except FileNotFoundError:
        return False


def mapping(x: T, in_min: T, in_max: T, out_min: T, out_max: T) -> T:
    """
    Map value from one range to another range

    :param x: value to map
    :type x: float/int
    :param in_min: input minimum
    :type in_min: float/int
    :param in_max: input maximum
    :type in_max: float/int
    :param out_min: output minimum
    :type out_min: float/int
    :param out_max: output maximum
    :type out_max: float/int
    :return: mapped value
    :rtype: float/int
    """
    result = (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
    if isinstance(x, int):
        return int(result)
    return result


def constrain(x: T, min_val: T, max_val: T):
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))


if __name__ == "main":
    reset_mcu_sync()
