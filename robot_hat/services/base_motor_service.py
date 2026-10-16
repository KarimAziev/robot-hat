import logging
import time
from abc import ABC, abstractmethod
from threading import RLock
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
        self._lock = RLock()
        self._closed = False

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
        with self._lock:
            first_error: Exception | None = None
            for _ in range(2):
                try:
                    self._stop_all()
                except Exception as error:
                    if first_error is None:
                        first_error = error
                time.sleep(0.002)
            if first_error is not None:
                raise first_error
            _log.debug("Motors stopped")

    def move(self, speed: float, direction: MotorServiceDirection) -> None:
        """
        Move the managed motor or motors.

        Args:
            speed: The base speed.
            direction: 1 for forward, -1 for backward, 0 for stopping.
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("Motor service is closed")
            try:
                self._move(speed, direction)
            except Exception:
                self._stop_after_failure()
                raise

    def _move(self, speed: float, direction: MotorServiceDirection) -> None:
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

    def _stop_after_failure(self) -> None:
        try:
            self.stop_all()
        except Exception:
            _log.exception("Failed to stop all motors after command failure")

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
        first_error: Exception | None = None
        for motor in self.motors:
            try:
                motor.stop()
            except Exception as error:
                if first_error is None:
                    first_error = error
        if first_error is not None:
            raise first_error
        self.direction = 0

    def close(self) -> None:
        """
        Close all managed motor resources.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            first_error: Exception | None = None
            try:
                self.stop_all()
            except Exception as error:
                first_error = error
            for motor in self.motors:
                try:
                    motor.close()
                except Exception as error:
                    _log.error("Error closing motor: %s", error)
                    if first_error is None:
                        first_error = error
            self._clear_motors()
            if first_error is not None:
                raise first_error

    def __del__(self) -> None:
        """
        Destructor method.
        """
        try:
            self.close()
        except Exception:
            _log.exception("Failed to close motor service during destruction")
