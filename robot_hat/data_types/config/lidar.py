from dataclasses import dataclass, field

from robot_hat.data_types.uart import UARTConfig


@dataclass(frozen=True)
class RPLidarC1Config:
    """RPLIDAR C1 serial and Standard scan-mode configuration."""

    port: str = "/dev/ttyUSB0"
    baudrate: int = 460800
    timeout: float = 1.0
    write_timeout: float = 1.0
    reset_wait_s: float = 2.0
    stop_wait_s: float = 0.1
    max_resync_bytes: int = field(default=64)

    def __post_init__(self) -> None:
        if not self.port:
            raise ValueError("port must not be empty")
        if self.baudrate <= 0:
            raise ValueError("baudrate must be greater than zero")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        if self.write_timeout <= 0:
            raise ValueError("write_timeout must be greater than zero")
        if self.reset_wait_s < 0:
            raise ValueError("reset_wait_s must be non-negative")
        if self.stop_wait_s < 0:
            raise ValueError("stop_wait_s must be non-negative")
        if self.max_resync_bytes < 1:
            raise ValueError("max_resync_bytes must be at least one")

    @property
    def uart_config(self) -> UARTConfig:
        return UARTConfig(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.write_timeout,
        )
