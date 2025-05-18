import logging
import time
from typing import List, Optional

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.ina219 import (
    ADCResolution,
    BusVoltageRange,
    Gain,
    INA219Config,
    Mode,
)
from robot_hat.interfaces.smbus_abc import SMBusABC

_log = logging.getLogger(__name__)

# Register addresses
REG_CONFIG = 0x00
REG_SHUNTVOLTAGE = 0x01
REG_BUSVOLTAGE = 0x02
REG_POWER = 0x03
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05


class INA219:
    """
    Driver for the INA219 sensor.

    This class handles low-level register accesses and sensor configuration.
    Most settings are configurable at initialization via an INA219Config instance.
    """

    def __init__(
        self,
        bus: BusType = 1,
        address: int = 0x41,
        config: Optional[INA219Config] = None,
    ) -> None:
        """
        Initialize the INA219 sensor.

        Parameters:
            i2c_bus: The I2C bus number. Ignored if bus_instance is provided.
            address: The I2C address of the sensor.
            config: An INA219Config instance with configuration settings.
            bus_instance: An optional pre-configured smbus2.SMBus instance for dependency injection.
        """
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

        self.config = config if config is not None else INA219Config()

        # Calibration parameters:
        self._current_lsb: float = self.config.current_lsb  # in mA per bit.
        self._cal_value: int = self.config.calibration_value
        self._power_lsb: float = self.config.power_lsb  # in W per bit

        # Write calibration and configuration registers.
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
        """
        Apply the configuration based on the config dataclass.
        This writes both the calibration and configuration registers.
        """
        # Write calibration register:
        self._write_register(REG_CALIBRATION, self._cal_value)

        # Build the 16-bit configuration value:
        # Bit positions: [15:13]=bus_voltage_range, [12:11]=gain,
        # [10:7]=bus ADC resolution, [6:3]=shunt ADC resolution, [2:0]=mode.
        config_value = (
            (self.config.bus_voltage_range.value << 13)
            | (self.config.gain.value << 11)
            | (self.config.bus_adc_resolution.value << 7)
            | (self.config.shunt_adc_resolution.value << 3)
            | (self.config.mode.value)
        )
        self._write_register(REG_CONFIG, config_value)

    def _write_register(self, reg: int, value: int) -> None:
        """
        Write a 16-bit integer to the specified register.

        Parameters:
            reg: Register address to write to.
            value: 16-bit integer value.
        """
        data = [(value >> 8) & 0xFF, value & 0xFF]
        try:
            self.bus.write_i2c_block_data(self.address, reg, data)
        except Exception as e:
            _log.error(f"Failed to write register 0x{reg:02X}: {e}")
            raise

    def _read_register(self, reg: int) -> int:
        """
        Read a 16-bit integer from the specified register.

        Parameters:
            reg: Register address to read from.

        Returns:
            Combined 16-bit value.
        """
        try:
            data: List[int] = self.bus.read_i2c_block_data(self.address, reg, 2)
            _log.debug(
                "Read from register %s (%s): at address %s (%s): data=%s",
                hex(reg),
                reg,
                hex(self.address),
                self.address,
                data,
            )
            return (data[0] << 8) | data[1]
        except Exception as e:
            _log.error(f"Failed to read register 0x{reg:02X}: {e}")
            raise

    def _refresh_calibration(self) -> None:
        """
        Refresh the calibration register.
        Some readings may require reloading calibration.
        """
        self._write_register(REG_CALIBRATION, self._cal_value)

    @staticmethod
    def _twos_complement(value: int, bits: int) -> int:
        """
        Compute the 2's complement of a given value.
        """
        if value & (1 << (bits - 1)):
            value -= 1 << bits
        return value

    def get_shunt_voltage_mv(self) -> float:
        """
        Get the shunt voltage in millivolts.
        The register value represents a 10µV per bit resolution.
        """
        self._refresh_calibration()
        raw = self._read_register(REG_SHUNTVOLTAGE)
        # INA219 shunt voltage register is a signed 16-bit value (10µV LSB).
        voltage = self._twos_complement(raw, 16)
        return voltage * 0.01  # 10 µV per bit = 0.01 mV per bit

    def get_bus_voltage_v(self) -> float:
        """
        Get the bus voltage in volts.
        The register output is right-shifted 3 bits and each bit equals 4mV.
        """
        self._refresh_calibration()
        raw = self._read_register(REG_BUSVOLTAGE)
        voltage = (raw >> 3) * 0.004
        return voltage

    def get_current_ma(self) -> float:
        """
        Get the current in milliamps.
        Uses the calibrated current LSB.
        """
        raw = self._read_register(REG_CURRENT)
        current = self._twos_complement(raw, 16)
        return current * self._current_lsb

    def get_power_w(self) -> float:
        """
        Get the power in watts.
        Uses the calibrated power LSB.
        """
        self._refresh_calibration()
        raw = self._read_register(REG_POWER)
        power = self._twos_complement(raw, 16)
        return power * self._power_lsb

    def update_config(self, new_config: INA219Config) -> None:
        """
        Update the configuration and reapply settings to the sensor.

        Parameters:
            new_config: A new INA219Config instance with updated settings.
        """
        self.config = new_config

        self._current_lsb = new_config.current_lsb
        self._cal_value = new_config.calibration_value
        self._power_lsb = new_config.power_lsb

        self._apply_configuration()

    def close(self) -> None:
        """
        Clean up or close any resources (like closing the I2C connection).
        """
        if self.own_bus:
            _log.debug("Closing SMBus")
            self.bus.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(message)s",
    )
    default_config = INA219Config(
        bus_voltage_range=BusVoltageRange.RANGE_32V,
        gain=Gain.DIV_8_320MV,
        bus_adc_resolution=ADCResolution.ADCRES_12BIT_32S,
        shunt_adc_resolution=ADCResolution.ADCRES_12BIT_32S,
        mode=Mode.SHUNT_AND_BUS_CONTINUOUS,
        current_lsb=0.1,  # 0.1 mA per bit
        calibration_value=4096,
        power_lsb=0.002,  # 20 × current_lsb in W per bit
    )

    ina219 = INA219(address=0x41, config=default_config)

    try:
        while True:
            bus_voltage = ina219.get_bus_voltage_v()
            # The shunt voltage reading is in mV. Convert to V.
            shunt_voltage = ina219.get_shunt_voltage_mv() / 1000.0
            current = ina219.get_current_ma()
            power = ina219.get_power_w()

            percent = (bus_voltage - 9) / 3.6 * 100
            percent = max(0, min(percent, 100))

            # Example output
            # 2025-04-06 13:44:53,604 - PSU Voltage:   11.706 V
            # 2025-04-06 13:44:53,604 - Shunt Voltage: -0.002230 V
            # 2025-04-06 13:44:53,605 - Load Voltage:  11.708 V
            # 2025-04-06 13:44:53,605 - Current:       -0.022300 A
            # 2025-04-06 13:44:53,605 - Power:          0.262 W
            # 2025-04-06 13:44:53,605 - Percent:       75.2%
            _log.info(f"PSU Voltage:   {(bus_voltage + shunt_voltage):6.3f} V")
            _log.info(f"Shunt Voltage: {shunt_voltage:9.6f} V")
            _log.info(f"Load Voltage:  {bus_voltage:6.3f} V")
            _log.info(f"Current:       {current/1000.0:9.6f} A")  # convert mA to A
            _log.info(f"Power:         {power:6.3f} W")

            _log.info(f"Percent:       {percent:3.1f}%")

            time.sleep(2)

    except KeyboardInterrupt:
        _log.info("Exiting on keyboard interrupt")
