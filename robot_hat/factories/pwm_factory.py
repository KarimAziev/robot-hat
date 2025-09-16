import logging
from typing import Dict, Optional, Type

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.pwm import PWMDriverConfig
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC

_log = logging.getLogger(__name__)

PWM_DRIVER_REGISTRY: Dict[str, Type[PWMDriverABC]] = {}


def register_pwm_driver(cls: Type[PWMDriverABC]) -> Type[PWMDriverABC]:
    """
    Decorator to register a PWM driver in the global registry.
    The class must have a DRIVER_TYPE attribute.

    The decorator stores the class in PWM_DRIVER_REGISTRY
    so the PWMFactory can later construct instances by name.

    Usage example:
    ```python
    @register_pwm_driver
    class PCA9685(PWMDriverABC):
        DRIVER_TYPE = "PCA9685"
        def __init__(
            self,
            address: int,
            bus: BusType = 1,
            period: int = 4096,
            frame_width: Optional[int] = 20000,
        ) -> None:
            super().__init__(bus=bus, address=address)
            # driver-specific init...
    ```
    """
    driver_type = getattr(cls, "DRIVER_TYPE", None)
    if driver_type is None:
        raise ValueError(
            f"Class {cls.__name__} must define a DRIVER_TYPE class attribute."
        )
    PWM_DRIVER_REGISTRY[driver_type] = cls
    return cls


class PWMFactory:
    @classmethod
    def create_pwm_driver(
        cls,
        config: PWMDriverConfig,
        bus: Optional[BusType] = None,
    ) -> PWMDriverABC:
        """
        Create and return a PWM driver instance from a given config.

        This will dynamically import available PWM drivers and look up the driver
        class registered under config.name.

        Args:
            config: PWMDriverConfig containing name, address, bus, frame_width, etc.
            bus: The I2C bus number or an already created instance of SMBus or
                 None. If none, the bus from config.bus is used.

        Returns:
            An instance of a class implementing PWM driver.
        """
        import robot_hat.drivers.pwm  # type: ignore

        driver_cls = PWM_DRIVER_REGISTRY[config.name]

        resolved_bus = bus if bus is not None else config.bus

        _log.debug(
            "Creating PWM driver %s on the address: %s (%s) with frame width %s µs",
            config.name,
            config.addr_str,
            config.address,
            config.frame_width,
        )

        return driver_cls(
            bus=resolved_bus,
            address=config.address,
            frame_width=config.frame_width,
        )
