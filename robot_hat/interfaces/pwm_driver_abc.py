"""
Abstract Base Class for PWM driver modules.
"""

import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import ClassVar, Optional, Type

from robot_hat.data_types.bus import BusType
from robot_hat.interfaces.smbus_abc import SMBusABC

_log = logging.getLogger(__name__)


class PWMDriverABC(ABC):
    """
    Abstract base class defining the interface for PWM drivers.

    Any driver used with the Servo class should implement these methods.
    """

    DRIVER_TYPE: ClassVar[str]

    def __init__(self, address: int, bus: BusType, **kwargs) -> None:
        """
        Initialize common attributes and the I2C bus, if needed.
        """
        self._address = address

        if isinstance(bus, int):
            from robot_hat.i2c.i2c_bus import I2CBus

            self._bus = I2CBus(bus)
            self._own_bus = True
            _log.debug("Created own SMBus on bus %d", bus)
        else:
            self._bus = bus
            self._own_bus = False
            _log.debug("Using injected SMBus instance")

    @property
    def address(self) -> int:
        return self._address

    @property
    def bus(self) -> SMBusABC:
        return self._bus

    @property
    def own_bus(self) -> bool:
        return self._own_bus

    def __enter__(self) -> "PWMDriverABC":
        """
        Optional: Provide support for context managers.
        """
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """
        Optional: Automatically close resources upon exiting the context.
        """
        if exc_type is not None:
            _log.error(
                f"An exception occurred during exiting exception type: {exc_type.__name__}"
            )
            if exc_value:
                _log.error(f"Exception value: {exc_value}")

            import traceback as tb

            if traceback:
                _log.error(f"Traceback: {''.join(tb.format_tb(traceback))}")
        self.close()

    def close(self) -> None:
        """
        Clean up or close any resources (like closing the I2C connection).
        """
        if self.own_bus:
            _log.debug("Closing SMBus")
            self.bus.close()

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
    def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
        """
        Set the PWM duty cycle for a specific channel.

        Args:
            channel: The channel number.
            duty: The duty cycle as a percentage.
        """
        pass
