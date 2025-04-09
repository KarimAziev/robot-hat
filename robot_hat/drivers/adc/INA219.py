import logging
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional, Union

from smbus2 import SMBus

from robot_hat.smbus_singleton import SMBus as SMBusSingleton

logger = logging.getLogger(__name__)

# Register addresses
REG_CONFIG = 0x00
REG_SHUNTVOLTAGE = 0x01
REG_BUSVOLTAGE = 0x02
REG_POWER = 0x03
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05


class BusVoltageRange(IntEnum):
    """
    Voltage range settings.
    """

    RANGE_16V = 0x00  # 16V
    RANGE_32V = 0x01  # 32V (default)


class Gain(IntEnum):
    """
    Gain settings for the shunt voltage measurement.
    """

    DIV_1_40MV = 0x00  # 1x gain, 40mV range
    DIV_2_80MV = 0x01  # 2x gain, 80mV range
    DIV_4_160MV = 0x02  # 4x gain, 160mV range
    DIV_8_320MV = 0x03  # 8x gain, 320mV range


class ADCResolution(IntEnum):
    """
    ADC resolution or averaging settings.
    """

    ADCRES_9BIT_1S = 0x00  # 9-bit, 1 sample, 84µs
    ADCRES_10BIT_1S = 0x01  # 10-bit, 1 sample, 148µs
    ADCRES_11BIT_1S = 0x02  # 11-bit, 1 sample, 276µs
    ADCRES_12BIT_1S = 0x03  # 12-bit, 1 sample, 532µs
    ADCRES_12BIT_2S = 0x09  # 12-bit, 2 samples, 1.06ms
    ADCRES_12BIT_4S = 0x0A  # 12-bit, 4 samples, 2.13ms
    ADCRES_12BIT_8S = 0x0B  # 12-bit, 8 samples, 4.26ms
    ADCRES_12BIT_16S = 0x0C  # 12-bit, 16 samples, 8.51ms
    ADCRES_12BIT_32S = 0x0D  # 12-bit, 32 samples, 17.02ms
    ADCRES_12BIT_64S = 0x0E  # 12-bit, 64 samples, 34.05ms
    ADCRES_12BIT_128S = 0x0F  # 12-bit, 128 samples, 68.10ms


class Mode(IntEnum):
    """
    Operating mode settings.
    """

    POWERDOWN = 0x00
    SHUNT_VOLT_TRIGGERED = 0x01
    BUS_VOLT_TRIGGERED = 0x02
    SHUNT_AND_BUS_TRIGGERED = 0x03
    ADC_OFF = 0x04
    SHUNT_VOLT_CONTINUOUS = 0x05
    BUS_VOLT_CONTINUOUS = 0x06
    SHUNT_AND_BUS_CONTINUOUS = 0x07


@dataclass
class INA219Config:
    """
    Sensor configuration settings.

    The calibration-related values (current_lsb, calibration_value, power_lsb)
    are tied to the shunt resistor and maximum current measurement range.
    """

    bus_voltage_range: BusVoltageRange = BusVoltageRange.RANGE_32V
    gain: Gain = Gain.DIV_8_320MV
    bus_adc_resolution: ADCResolution = ADCResolution.ADCRES_12BIT_32S
    shunt_adc_resolution: ADCResolution = ADCResolution.ADCRES_12BIT_32S
    mode: Mode = Mode.SHUNT_AND_BUS_CONTINUOUS

    # Calibration parameters:
    current_lsb: float = 0.1  # in mA/bit (e.g., for 0.1 mA per bit)
    calibration_value: int = (
        4096  # Calibration register value (magic number based on shunt resistor)
    )
    power_lsb: float = 0.002  # in W/bit (e.g., 20 * current_lsb)


class INA219:
    """
    Driver for the INA219 sensor.

    This class handles low-level register accesses and sensor configuration.
    Most settings are configurable at initialization via an INA219Config instance.
    """

    def __init__(
        self,
        bus_num: int = 1,
        address: int = 0x41,
        config: Optional[INA219Config] = None,
        bus: Union[SMBusSingleton, SMBus, None] = None,
    ) -> None:
        """
        Initialize the INA219 sensor.

        Parameters:
            i2c_bus: The I2C bus number. Ignored if bus_instance is provided.
            addr: The I2C address of the sensor.
            config: An INA219Config instance with configuration settings.
            bus_instance: An optional pre-configured smbus2.SMBus instance for dependency injection.
        """
        self.addr = address
        self.config = config if config is not None else INA219Config()

        self._bus_num: int = bus_num
        if bus is None:
            self.bus = SMBus(bus_num)
            self._own_bus: bool = True
            logger.debug("Created own SMBus on bus %d", bus_num)
        else:
            self.bus = bus
            self._own_bus = False
            logger.debug("Using injected SMBus instance")

        # Calibration parameters:
        self._current_lsb: float = self.config.current_lsb  # in mA per bit.
        self._cal_value: int = self.config.calibration_value
        self._power_lsb: float = self.config.power_lsb  # in W per bit

        # Write calibration and configuration registers.
        self._apply_configuration()

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
            self.bus.write_i2c_block_data(self.addr, reg, data)
        except Exception as e:
            logger.error(f"Failed to write register 0x{reg:02X}: {e}")
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
            data: List[int] = self.bus.read_i2c_block_data(self.addr, reg, 2)
            return (data[0] << 8) | data[1]
        except Exception as e:
            logger.error(f"Failed to read register 0x{reg:02X}: {e}")
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
        Close the underlying resources.
        """
        if self._own_bus:
            logger.debug("Closing SMBus on bus %d", self._bus_num)
            self.bus.close()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
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
            logger.info(f"PSU Voltage:   {(bus_voltage + shunt_voltage):6.3f} V")
            logger.info(f"Shunt Voltage: {shunt_voltage:9.6f} V")
            logger.info(f"Load Voltage:  {bus_voltage:6.3f} V")
            logger.info(f"Current:       {current/1000.0:9.6f} A")  # convert mA to A
            logger.info(f"Power:         {power:6.3f} W")

            logger.info(f"Percent:       {percent:3.1f}%")

            time.sleep(2)

    except KeyboardInterrupt:
        logger.info("Exiting on keyboard interrupt")
