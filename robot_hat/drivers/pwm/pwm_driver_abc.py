"""
Abstract Base Class for PWM driver modules.
"""

from abc import ABC, abstractmethod


class PWMDriverABC(ABC):
    """
    Abstract base class defining the interface for PWM drivers.

    Any driver used with the Servo class should implement these methods.
    """

    @abstractmethod
    def set_pwm_freq(self, freq: int) -> None:
        """
        Set the PWM frequency.

        Args:
            freq: Frequency in Hz.
        """
        pass

    @abstractmethod
    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        """
        Set the servo pulse for a specific channel.

        Args:
            channel: The channel number (e.g. 0-15).
            pulse: The pulse width in microseconds (µs).
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """
        Clean up or close any resources (like closing the I2C connection).
        """
        pass

    def __enter__(self) -> "PWMDriverABC":
        """
        Optional: Provide support for context managers.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        """
        Optional: Automatically close resources upon exiting the context.
        """
        self.close()
