import logging
import random
import time
from typing import List

from robot_hat.ultrasonic import Ultrasonic as UltrasonicOrig

logger = logging.getLogger(__name__)


def generate_ultrasonic_measurements(
    start: float, end: float, step: float
) -> List[float]:
    """
    Generate a sequence of ultrasonic measurements with random floats.

    :param start: Starting distance (inclusive).
    :param end: Ending distance (inclusive).
    :param step: Step size for descending values.
    :return: List of distances in descending order.
    """
    measurements = []
    current = start
    while current >= end:
        measurements.append(float(current + random.uniform(-1.5, 1.5)))
        current -= step
    return measurements


class Ultrasonic(UltrasonicOrig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_idx = 0
        self.ultrasonic_sequence = generate_ultrasonic_measurements(400, 20, 10)

    def _read(self) -> float:
        """
        Simulate a single distance measurement.
        """
        self.trig.off()
        time.sleep(0.001)
        self.trig.on()
        time.sleep(0.00001)
        self.trig.off()

        if self._current_idx >= len(self.ultrasonic_sequence):
            self._current_idx = 0
        result = self.ultrasonic_sequence[self._current_idx]
        self._current_idx += 1
        return result


if __name__ == "__main__":
    import os

    os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
    os.environ["ROBOT_HAT_MOCK_SMBUS"] = "1"
    from robot_hat.pin import Pin

    ultrasonic = Ultrasonic(Pin("D2"), Pin("D3"))

    for i in range(45):
        result = ultrasonic.read()
        print(f"f {i}: {result}")
