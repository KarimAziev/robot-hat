from dataclasses import dataclass
from enum import IntEnum


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
