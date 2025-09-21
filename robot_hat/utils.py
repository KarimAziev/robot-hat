import logging
import os
import re
from functools import lru_cache, reduce
from typing import Callable, Optional, TypeVar

T = TypeVar("T", int, float)

logger = logging.getLogger(__name__)


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


def constrain(x: T, min_val: T, max_val: T) -> T:
    """
    Constrains value to be within a range.
    """
    return max(min_val, min(max_val, x))


def parse_int_suffix(s: str) -> Optional[int]:
    match = re.search(r"(\d+)$", s)
    if match:
        return int(match.group(1))
    return None


@lru_cache()
def get_gpio_factory_name() -> str:
    """
    Determines the appropriate GPIO factory name based on the Raspberry Pi model.

    This function reads the device-tree model information from the system.
    - If the model indicates a Raspberry Pi 5, it returns "lgpio".
    - If the model indicates any other Raspberry Pi, it returns "rpigpio".
    - In case of any error or if the model file is missing, it returns "mock".

    Returns:
        The GPIO factory name to use.
    """
    model_path = "/proc/device-tree/model"
    if os.path.exists(model_path):
        try:
            with open(model_path, "rb") as f:
                model_bytes = f.read()
                model_str = model_bytes.decode("utf-8").strip("\x00").lower()
                if "raspberry pi 5" in model_str:
                    return "lgpio"
                elif "raspberry pi" in model_str:
                    return "rpigpio"
        except Exception as e:
            logger.error("Error reading model file: %s", e)
            return "mock"
    return "mock"


def setup_env_vars() -> bool:
    """
    Set up environment variables related to GPIO and platform detection.
    Returns True if running on a real Raspberry Pi, False otherwise.
    """
    if os.getenv("GPIOZERO_PIN_FACTORY") is None:
        gpio_factory_name = get_gpio_factory_name()
        os.environ["GPIOZERO_PIN_FACTORY"] = gpio_factory_name
        is_real_raspberry = gpio_factory_name != "mock"
    else:
        is_real_raspberry = is_raspberry_pi()

    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    if not is_real_raspberry:
        for key, value in [
            ("ROBOT_HAT_MOCK_SMBUS", "1"),
            ("ROBOT_HAT_DISCHARGE_RATE", "10"),
        ]:
            os.environ.setdefault(key, value)

    return is_real_raspberry
