from abc import ABC, abstractmethod
from typing import Sequence


class SPIABC(ABC):
    """Minimal, injectable full-duplex SPI device boundary.

    Implementations represent one already-selected chip-select device. Protocol
    details such as mode and maximum clock rate are configured by the concrete
    device when it is constructed.
    """

    @abstractmethod
    def transfer(self, data: Sequence[int]) -> list[int]:
        """Exchange one chip-select-bounded byte sequence."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release resources owned by this SPI device."""
        pass


__all__ = ["SPIABC"]
