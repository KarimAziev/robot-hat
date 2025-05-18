import logging
from typing import Dict, Optional, Type

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.pwm import PWMDriverConfig
from robot_hat.interfaces import PWMDriverABC

_log = logging.getLogger(__name__)

PWM_DRIVER_REGISTRY: Dict[str, Type[PWMDriverABC]] = {}


def register_pwm_driver(cls: Type[PWMDriverABC]) -> Type[PWMDriverABC]:
    """
    Decorator to register a PWM driver in the global registry.
    The class must have a DRIVER_TYPE attribute.
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
