import logging
from typing import List, Optional

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.ina260 import INA260Config
from robot_hat.interfaces.smbus_abc import SMBusABC

_log = logging.getLogger(__name__)

REG_CONFIG = 0x00
REG_CURRENT = 0x01
REG_BUSVOLTAGE = 0x02
REG_POWER = 0x03
REG_MASK_ENABLE = 0x06
REG_ALERT_LIMIT = 0x07
REG_MANUFACTURER_ID = 0xFE
REG_DIE_ID = 0xFF

TI_MANUFACTURER_ID = 0x5449
INA260_DEVICE_ID = 0x260


class INA260:
    """Driver for the INA260 current and power monitoring sensor."""

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x40,
        config: Optional[INA260Config] = None,
        *,
        validate_device_id: bool = False,
    ) -> None:
        self._address = address

        if isinstance(bus, int):
            from robot_hat.i2c.i2c_bus import I2CBus

            self._bus = I2CBus(bus)
            self._own_bus = True
            _log.debug("Created new SMBus instance for INA260 on bus %d", bus)
        else:
            self._bus = bus
            self._own_bus = False
            _log.debug("Using injected SMBus instance for INA260")

        self.config = config if config is not None else INA260Config()
        self._apply_configuration()

        if validate_device_id:
            self._validate_device_signature()

    @property
    def address(self) -> int:
        return self._address

    @property
    def bus(self) -> SMBusABC:
        return self._bus

    @property
    def own_bus(self) -> bool:
        return self._own_bus

    def _validate_device_signature(self) -> None:
        manufacturer = self._read_register(REG_MANUFACTURER_ID)
        device = self._read_register(REG_DIE_ID) & 0x0FFF
        if manufacturer != TI_MANUFACTURER_ID:
            raise RuntimeError(
                f"Unexpected manufacturer ID 0x{manufacturer:04X} (expected 0x{TI_MANUFACTURER_ID:04X})"
            )
        if device != INA260_DEVICE_ID:
            raise RuntimeError(
                f"Unexpected device ID 0x{device:03X} (expected 0x{INA260_DEVICE_ID:03X})"
            )

    def _apply_configuration(self) -> None:
        config_value = self.config.to_register_value()
        self._write_register(REG_CONFIG, config_value)

        if self.config.alert_mask:
            self._write_register(REG_MASK_ENABLE, self.config.alert_mask)
        if self.config.alert_limit:
            self._write_register(REG_ALERT_LIMIT, self.config.alert_limit)

    def _write_register(self, reg: int, value: int) -> None:
        data = [(value >> 8) & 0xFF, value & 0xFF]
        try:
            self.bus.write_i2c_block_data(self.address, reg, data)
        except Exception as exc:
            _log.error("Failed to write register 0x%02X on INA260: %s", reg, exc)
            raise

    def _read_register(self, reg: int) -> int:
        try:
            data: List[int] = self.bus.read_i2c_block_data(self.address, reg, 2)
            return (data[0] << 8) | data[1]
        except Exception as exc:
            _log.error("Failed to read register 0x%02X on INA260: %s", reg, exc)
            raise

    @staticmethod
    def _to_twos_complement(value: int, bits: int) -> int:
        if value & (1 << (bits - 1)):
            value -= 1 << bits
        return value

    def get_current_ma(self) -> float:
        """Return the measured current in milliamps."""
        raw = self._read_register(REG_CURRENT)
        signed = self._to_twos_complement(raw & 0xFFFF, 16)
        return signed * INA260Config.CURRENT_LSB_MA

    def get_bus_voltage_v(self) -> float:
        """Return the bus voltage in volts."""
        raw = self._read_register(REG_BUSVOLTAGE)
        return (raw & 0xFFFF) * INA260Config.BUS_VOLTAGE_LSB_V

    def get_power_mw(self) -> float:
        """Return the measured power in milliwatts."""
        raw = self._read_register(REG_POWER)
        signed = self._to_twos_complement(raw & 0xFFFF, 16)
        return signed * INA260Config.POWER_LSB_MW

    def get_shunt_voltage_mv(self) -> float:
        """Return the estimated shunt voltage drop in millivolts."""
        current_ma = self.get_current_ma()
        return current_ma * self.config.shunt_resistance_ohms

    def update_config(self, new_config: INA260Config) -> None:
        self.config = new_config
        self._apply_configuration()

    def close(self) -> None:
        if self.own_bus:
            _log.debug("Closing SMBus for INA260")
            self.bus.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    driver = INA260(bus=1, address=0x40, validate_device_id=False)
    try:
        current_ma = driver.get_current_ma()
        voltage_v = driver.get_bus_voltage_v()
        power_mw = driver.get_power_mw()
        print(
            f"Current: {current_ma:.2f} mA | Voltage: {voltage_v:.3f} V | Power: {power_mw/1000.0:.3f} W"
        )
    finally:
        driver.close()
