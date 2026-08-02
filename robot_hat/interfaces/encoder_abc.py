from abc import ABC, abstractmethod

from robot_hat.data_types.encoder import EncoderSample


class EncoderABC(ABC):
    """Vendor-neutral interface for one signed cumulative wheel encoder."""

    @abstractmethod
    def initialize(self) -> None:
        """Configure counting resources and begin observing encoder edges."""
        pass

    @abstractmethod
    def read_sample(self) -> EncoderSample:
        """Return the current cumulative counter and its observation time."""
        pass

    @abstractmethod
    def reset(self, ticks: int = 0) -> None:
        """Atomically set the cumulative software counter."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Stop edge observation and release owned resources."""
        pass


__all__ = ["EncoderABC"]
