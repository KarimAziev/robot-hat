import logging
from typing import List, Optional

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.ina226 import INA226Config
from robot_hat.interfaces.smbus_abc import SMBusABC

_log = logging.getLogger(__name__)

REG_CONFIG = 0x00
REG_SHUNTVOLTAGE = 0x01
REG_BUSVOLTAGE = 0x02
REG_POWER = 0x03
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05
REG_MASK = 0x06
REG_ALERT_LIMIT = 0x07
REG_MANUFACTURER_ID = 0xFE
REG_DIE_ID = 0xFF


class INA226:
    """
    Driver for the INA226 sensor.

    Notes:
      - config.current_lsb is in A/bit.
      - get_current_ma returns milliamps (mA).
      - get_power_mw returns milliwatts (mW).
      - get_shunt_voltage_mv returns millivolts (mV).
      - get_bus_voltage_v returns volts (V).
    """

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x40,
        config: Optional[INA226Config] = None,
    ) -> None:
        self._address = address

        if isinstance(bus, int):
            from robot_hat.i2c.i2c_bus import I2CBus

            self._bus = I2CBus(bus)
            self._own_bus = True
            _log.debug("Created own SMBus on bus %d", bus)
        else:
            self._bus = bus
            self._own_bus = False
            _log.debug("Using injected SMBus instance")

        self.config = config if config is not None else INA226Config()

        self._current_lsb = self.config.current_lsb
        self._calibration_value = self.config.calibration_value
        self._power_lsb = self.config.power_lsb

        self._apply_configuration()

    @property
    def address(self) -> int:
        return self._address

    @property
    def bus(self) -> SMBusABC:
        return self._bus

    @property
    def own_bus(self) -> bool:
        return self._own_bus

    def _apply_configuration(self) -> None:
        self._write_register(REG_CALIBRATION, self._calibration_value)

        config_value = (
            (self.config.avg_mode.value << 9)
            | (self.config.bus_conv_time.value << 6)
            | (self.config.shunt_conv_time.value << 3)
            | (self.config.mode.value)
            | (1 << 14)
        )

        self._write_register(REG_CONFIG, config_value)

    def _write_register(self, reg: int, value: int) -> None:
        data = [(value >> 8) & 0xFF, value & 0xFF]
        try:
            self.bus.write_i2c_block_data(self.address, reg, data)
        except Exception as e:
            _log.error(f"Failed to write register 0x{reg:02X}: {e}")
            raise

    def _read_register(self, reg: int) -> int:
        try:
            data: List[int] = self.bus.read_i2c_block_data(self.address, reg, 2)
            return (data[0] << 8) | data[1]
        except Exception as e:
            _log.error(f"Failed to read register 0x{reg:02X}: {e}")
            raise

    @staticmethod
    def _twos_complement(value: int, bits: int) -> int:
        if value & (1 << (bits - 1)):
            value -= 1 << bits
        return value

    def refresh_calibration(self) -> None:
        """Re-write the calibration register (safe to call before reads)."""
        self._write_register(REG_CALIBRATION, self._calibration_value)

    def get_shunt_voltage_mv(self) -> float:
        """
        Read shunt voltage register and return millivolts.

        INA226 shunt register LSB = 2.5 uV per bit => 0.0025 mV/bit.
        """
        self.refresh_calibration()
        raw = self._read_register(REG_SHUNTVOLTAGE)
        signed = self._twos_complement(raw & 0xFFFF, 16)
        return signed * INA226Config.SHUNT_LSB_MV

    def get_bus_voltage_v(self) -> float:
        """
        Read bus voltage register and return volts.

        INA226 bus register LSB = 1.25 mV per bit.
        """
        self.refresh_calibration()
        raw = self._read_register(REG_BUSVOLTAGE)
        return (raw & 0xFFFF) * (INA226Config.BUS_LSB_MV / 1000.0)

    def get_current_ma(self) -> float:
        """
        Read current register and return milliamps.

        current_lsb in config is A/bit, so multiply and convert to mA.
        """
        raw = self._read_register(REG_CURRENT)
        signed = self._twos_complement(raw & 0xFFFF, 16)
        return signed * self._current_lsb * 1000.0

    def get_power_mw(self) -> float:
        """
        Read power register and return milliwatts.

        power_lsb is W/bit; multiply and convert to mW.
        """
        self.refresh_calibration()
        raw = self._read_register(REG_POWER)
        signed = self._twos_complement(raw & 0xFFFF, 16)
        return signed * self._power_lsb * 1000.0

    def update_config(self, new_config: INA226Config) -> None:
        """
        Replace config and re-apply calibration + configuration.
        """
        self.config = new_config
        self._current_lsb = new_config.current_lsb
        self._calibration_value = new_config.calibration_value
        self._power_lsb = new_config.power_lsb
        self._apply_configuration()

    def close(self) -> None:
        if self.own_bus:
            _log.debug("Closing SMBus")
            self.bus.close()


if __name__ == "__main__":
    import logging
    import time

    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    config = INA226Config.from_shunt(shunt_ohms=0.002, max_expected_amps=10.0)

    ina = INA226(bus=1, address=0x40, config=config)

    try:
        while True:
            bus_v = ina.get_bus_voltage_v()

            shunt_v_mv = ina.get_shunt_voltage_mv()
            shunt_v = shunt_v_mv / 1000.0

            current_ma = ina.get_current_ma()
            current_a = current_ma / 1000.0

            power_mw = ina.get_power_mw()
            power_w = power_mw / 1000.0

            percent = (bus_v - 9.0) / 3.6 * 100.0
            percent = max(0.0, min(percent, 100.0))

            _log.info("PSU Voltage:   %6.3f V", bus_v + shunt_v)
            _log.info("Shunt Voltage: %9.6f V", shunt_v)
            _log.info("Load Voltage:  %6.3f V", bus_v)
            _log.info("Current:       %9.6f A", current_a)
            _log.info("Power:         %6.3f W", power_w)
            _log.info("Percent:       %3.1f%%", percent)

            time.sleep(2.0)

    except KeyboardInterrupt:
        _log.info("Exiting on keyboard interrupt")
    finally:
        ina.close()
