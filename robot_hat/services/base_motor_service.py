import logging
import time
from abc import ABC, abstractmethod
from typing import Sequence

from robot_hat.data_types.motor import MotorServiceDirection
from robot_hat.interfaces.motor_abc import MotorABC

_log = logging.getLogger(__name__)


class BaseMotorService(ABC):
    """
    Shared lifecycle and movement behavior for motor service classes.
    """

    def __init__(self) -> None:
        self.direction: MotorServiceDirection = 0

    @property
    @abstractmethod
    def motors(self) -> Sequence[MotorABC]:
        """
        Return the currently managed motor instances.
        """
        pass

    @property
    @abstractmethod
    def speed(self) -> float:
        """
        Return the current service speed.
        """
        pass

    @abstractmethod
    def _set_motion(self, speed: float, direction: MotorServiceDirection) -> None:
        """
        Apply a non-zero movement command to the managed motor or motors.
        """
        pass

    @abstractmethod
    def _clear_motors(self) -> None:
        """
        Clear managed motor references after close.
        """
        pass

    def stop_all(self) -> None:
        """
        Stop all managed motors safely with a double-pulse mechanism.
        """
        _log.debug("Stopping motors")
        self._stop_all()
        time.sleep(0.002)
        self._stop_all()
        time.sleep(0.002)
        _log.debug("Motors Stopped")

    def move(self, speed: float, direction: MotorServiceDirection) -> None:
        """
        Move the managed motor or motors.

        Args:
            speed: The base speed.
            direction: 1 for forward, -1 for backward, 0 for stopping.
        """
        if direction == 0 and abs(speed) > 0:
            _log.warning(
                "Non-zero speed provided with direction 0; motors will be stopped."
            )

        if direction == 0:
            self.stop_all()
            return

        if not self.motors:
            raise AssertionError("No motors are available")

        self._set_motion(speed, direction)
        self.direction = direction

    def reset_calibration(self) -> None:
        """
        Reset direction and speed calibration for all managed motors.
        """
        for motor in self.motors:
            motor.reset_calibration_direction()
            motor.reset_calibration_speed()

    def _stop_all(self) -> None:
        """
        Stop all managed motors immediately.
        """
        for motor in self.motors:
            motor.stop()
        self.direction = 0

    def close(self) -> None:
        """
        Close all managed motor resources.
        """
        for motor in self.motors:
            try:
                motor.close()
            except Exception as e:
                _log.error("Error closing motor: %s", e)
        self._clear_motors()

    def __del__(self) -> None:
        """
        Destructor method.
        """
        self.close()
