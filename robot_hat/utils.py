import logging
import os
import re
from functools import lru_cache, reduce
from typing import Callable, Optional, TypeVar

T = TypeVar("T", int, float)

_log = logging.getLogger(__name__)


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


@lru_cache()
def get_device_model() -> str | None:
    """
    Read the device model string from the system device tree.

    This function attempts to read `/proc/device-tree/model` and returns
    the decoded model string in lowercase.

    If the file cannot be read, decoded, or does not exist, `None` is returned.
    """
    model_path = "/proc/device-tree/model"

    try:
        with open(model_path, "rb") as f:
            return f.read().decode("utf-8").strip("\x00").lower()
    except FileNotFoundError:
        _log.debug("%s not found, assuming this is not a Raspberry Pi", model_path)
        return None
    except PermissionError:
        _log.debug(
            "Permission denied reading %s, assuming this is not a Raspberry Pi",
            model_path,
        )
        return None
    except UnicodeDecodeError as e:
        _log.debug(
            "Could not decode %s (%s); assuming this is not a Raspberry Pi",
            model_path,
            e,
        )
        return None
    except OSError as e:
        _log.debug(
            "Failed to read %s (%s), assuming this is not a Raspberry Pi", model_path, e
        )
        return None
    except Exception:
        _log.exception(
            "Unexpected error while reading %s, assuming this is not a Raspberry Pi",
            model_path,
        )
        return None


def is_raspberry_pi() -> bool:
    """
    Check if the current operating system is running on a Raspberry Pi.

    Returns:
        bool: True if the OS is running on a Raspberry Pi, False otherwise.
    """
    model_info = get_device_model()
    return model_info is not None and "raspberry pi" in model_info


def mapping(x: T, in_min: T, in_max: T, out_min: T, out_max: T) -> T:
    """
    Map a value from one range to another.

    Args:
        x: The value to map.
        in_min: The lower bound of the input range.
        in_max: The upper bound of the input range.
        out_min: The lower bound of the output range.
        out_max: The upper bound of the output range.

    Returns:
        The mapped value in the output range. If ``x`` is an integer,
        the result is returned as an integer; otherwise, a float is returned.
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
    model_info = get_device_model()
    mock_factory_name = "mock"

    if model_info is None:
        return mock_factory_name
    if "raspberry pi 5" in model_info:
        return "lgpio"
    if "raspberry pi" in model_info:
        return "rpigpio"

    return mock_factory_name


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
