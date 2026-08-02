from dataclasses import dataclass


@dataclass(frozen=True)
class EncoderSample:
    """A timestamped snapshot of one signed cumulative encoder counter.

    Positive direction is defined by the concrete driver configuration. Delta
    ticks are deliberately not stored here because deriving a delta is a
    consumer concern and must not mutate the hardware reading API.
    """

    ticks: int
    timestamp_monotonic_ns: int

    def __post_init__(self) -> None:
        if self.timestamp_monotonic_ns < 0:
            raise ValueError("timestamp_monotonic_ns must be non-negative")


__all__ = ["EncoderSample"]
