import logging
import threading
from typing import TYPE_CHECKING, Dict, Union

from robot_hat.exceptions import InvalidBusType

if TYPE_CHECKING:
    from robot_hat.i2c.i2c_bus import I2CBus

_log = logging.getLogger(__name__)


class SMBusManager:
    _instances: Dict[str, "I2CBus"] = {}
    _lock = threading.RLock()

    @classmethod
    def _normalize_bus(cls, bus: Union[int, str]) -> str:
        if isinstance(bus, int):
            filepath = "/dev/i2c-{}".format(bus)
        elif isinstance(bus, str):
            filepath = bus
        else:
            raise InvalidBusType("Unexpected type(bus)={}".format(type(bus)))
        return filepath

    @classmethod
    def _on_bus_close(cls, closed_bus: "I2CBus") -> None:
        normalized_bus = cls._normalize_bus(closed_bus._bus)
        with cls._lock:
            if normalized_bus in cls._instances:
                _log.debug("Removing closed bus %s from instances", normalized_bus)
                cls._instances.pop(normalized_bus, None)

    @classmethod
    def get_bus(cls, bus: Union[int, str], force: bool = False) -> "I2CBus":
        """
        Return a singleton I2CBus instance for the given bus.
        If an instance does not exist yet, one is created and stored.
        """
        normalized_bus = cls._normalize_bus(bus)

        with cls._lock:
            instance = cls._instances.get(normalized_bus)
            if instance:
                _log.debug(
                    "Reusing existing I2CBus instance for bus %s", normalized_bus
                )
                return instance

        _log.debug(
            "Creating I2CBus instance for bus %s (force=%s)", normalized_bus, force
        )
        try:
            from robot_hat.i2c.i2c_bus import I2CBus

            new_instance = I2CBus(normalized_bus, force)
            new_instance.emitter.on("close", cls._on_bus_close)
        except Exception as e:
            _log.error("Error while creating I2CBus for %s: %s", normalized_bus, e)
            raise

        with cls._lock:
            instance = cls._instances.get(normalized_bus)
            if instance is None:
                cls._instances[normalized_bus] = new_instance
                instance = new_instance
            else:
                _log.debug(
                    "Another thread already created bus %s; closing duplicate instance",
                    normalized_bus,
                )
                try:
                    new_instance.close()
                except Exception:
                    pass
        return instance

    @classmethod
    def close_bus(cls, bus: Union[int, str]) -> None:
        """
        Closes the I2CBus instance for the given bus and removes it from the manager.
        """
        normalized_bus = cls._normalize_bus(bus)
        with cls._lock:
            instance = cls._instances.pop(normalized_bus, None)
        if instance:
            _log.debug("Closing I2CBus instance for bus %s", normalized_bus)
            try:
                instance.emitter.off("close", cls._on_bus_close)
                instance.close()
            except Exception as err:
                _log.error("Error while closing bus %s: %s", normalized_bus, err)
        else:
            _log.warning("No I2CBus instance found for bus %s to close", normalized_bus)

    @classmethod
    def close_all(cls) -> None:
        """
        Closes all I2CBus instances and clears the instances dictionary.
        """
        with cls._lock:
            buses = list(cls._instances.keys())
        for bus in buses:
            cls.close_bus(bus)


if __name__ == "__main__":
    from robot_hat.utils import setup_env_vars

    setup_env_vars()
    bus0 = SMBusManager.get_bus(0)
    bus1 = SMBusManager.get_bus(1)
    bus0_again = SMBusManager.get_bus(0)

    print("bus0 is bus0_again:", bus0 is bus0_again)  # bus0 is bus0_again: True

    SMBusManager.close_bus(0)
    SMBusManager.close_all()
