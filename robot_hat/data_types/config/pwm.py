from dataclasses import dataclass, field


@dataclass
class PWMDriverConfig:
    """
    The configuration parameters to control a PWM driver chip via the I2C bus.
    """

    address: int = field(
        metadata={
            "title": "I2C address",
            "description": "I2C address of the device",
        }
    )

    @property
    def addr_str(self) -> str:
        """Return address as a hex string."""
        return hex(self.address)

    name: str = field(
        metadata={
            "description": "Model of the PWM driver chip",
            "examples": ["Sunfounder", "PCA9685"],
        },
    )

    bus: int = field(
        default=1,
        metadata={
            "title": "The I2C bus",
            "description": "The I2C bus number used to communicate with the PWM driver chip.",
            "examples": [1, 4],
        },
    )
    frame_width: int = field(
        default=20000,
        metadata={
            "title": "Frame Width in µs",
            "description": (
                "Determines the full cycle duration between servo control pulses in microseconds. "
                "This value represents the period in which all servo channels are refreshed. "
                "A typical servo expects a pulse every 20000 µs (20 ms), and altering this value can affect "
                "the overall responsiveness and timing sensitivity of the servo's control signal."
            ),
            "examples": [20000],
        },
    )
    freq: int = field(
        default=50,
        metadata={
            "title": "PWM frequency (Hz)",
            "description": (
                "The PWM frequency in Hertz which controls the granularity of the pulse width modulation. "
                "Higher frequencies allow for more precise adjustments of the pulse width (duty cycle), "
                "resulting in smoother and more accurate servo movements. Conversely, lower frequencies might lead "
                "to coarser control."
            ),
            "examples": [50],
        },
    )

    def __post_init__(self) -> None:
        if not (0 <= self.address <= 0x7F):
            raise ValueError(
                f"I2C address {self.address} is out of valid range (0-0x7F)."
            )

        if self.bus < 0:
            raise ValueError(f"I2C bus number must be non-negative. Got: {self.bus}")

        if self.frame_width < 1:
            raise ValueError(
                f"Frame width must be at least 1 µs. Got: {self.frame_width}"
            )

        if self.freq <= 0:
            raise ValueError(f"PWM frequency must be greater than 0. Got: {self.freq}")
