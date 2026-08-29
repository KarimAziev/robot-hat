"""Hardware-neutral digital input with notifications on both signal edges."""

from abc import ABC, abstractmethod
from typing import Callable


DigitalEdgeCallback = Callable[[], None]


class DigitalEdgeInputABC(ABC):
    """One logical digital input suitable for raw encoder edge capture."""

    @abstractmethod
    def initialize(self) -> None:
        """Open the input without installing software debounce."""
        pass

    @abstractmethod
    def read(self) -> bool:
        """Read the current logical input level."""
        pass

    @abstractmethod
    def set_edge_callback(self, callback: DigitalEdgeCallback | None) -> None:
        """Invoke ``callback`` on both rising and falling logical edges."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Detach callbacks and release owned input resources idempotently."""
        pass


__all__ = ["DigitalEdgeCallback", "DigitalEdgeInputABC"]
