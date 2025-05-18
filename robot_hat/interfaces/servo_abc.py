"""
Abstract Base Class for servo implementations.
"""

from abc import ABC, abstractmethod


class ServoABC(ABC):
    @abstractmethod
    def angle(self, angle: float) -> None:
        """
        Set the servo to the specified angle.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """
        Reset servo to its default position.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Clean up any resources.
        """
        pass

    def pulse_width_time(self, pulse_width_time: float) -> None:
        """
        Directly set the pulse width in microseconds.
        This base implementation raises NotImplementedError.
        """
        raise NotImplementedError("Direct PWM control is not implemented.")
