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


@dataclass(frozen=True)
class EncoderHealth:
    """Vendor-neutral encoder availability and diagnostic counters.

    Hardware-specific fields remain ``None`` when a sensor cannot report them.
    Counters are cumulative since construction of the concrete encoder.
    """

    available: bool
    magnet_detected: bool | None = None
    magnet_too_weak: bool | None = None
    magnet_too_strong: bool | None = None
    communication_errors: int = 0
    invalid_transitions: int = 0

    def __post_init__(self) -> None:
        if self.communication_errors < 0:
            raise ValueError("communication_errors must be non-negative")
        if self.invalid_transitions < 0:
            raise ValueError("invalid_transitions must be non-negative")


__all__ = ["EncoderHealth", "EncoderSample"]
