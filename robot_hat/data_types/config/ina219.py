import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


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

    bus_voltage_range: BusVoltageRange = field(
        default=BusVoltageRange.RANGE_32V,
        metadata={"desc": "Bus voltage measurement range setting"},
    )
    gain: Gain = field(
        default=Gain.DIV_8_320MV,
        metadata={"desc": "PGA gain (shunt voltage full-scale range)"},
    )
    bus_adc_resolution: ADCResolution = field(
        default=ADCResolution.ADCRES_12BIT_32S,
        metadata={"desc": "Bus ADC resolution / averaging"},
    )
    shunt_adc_resolution: ADCResolution = field(
        default=ADCResolution.ADCRES_12BIT_32S,
        metadata={"desc": "Shunt ADC resolution / averaging"},
    )
    mode: Mode = field(
        default=Mode.SHUNT_AND_BUS_CONTINUOUS,
        metadata={"desc": "Operating mode"},
    )

    # Calibration parameters:
    current_lsb: float = field(
        default=0.1,  # mA/bit
        metadata={"units": "mA/bit", "derived": "Use from_shunt() to compute"},
    )
    calibration_value: int = field(
        default=4096,
        metadata={"units": "reg", "desc": "16-bit calibration register value"},
    )
    power_lsb: float = field(
        default=0.002,  # W/bit
        metadata={"units": "W/bit", "derived": "20 × Current_LSB (A)"},
    )

    @staticmethod
    def _round_up_to_step(value: float, step: float) -> float:
        if step <= 0:
            return value
        return math.ceil(value / step) * step

    @staticmethod
    def _select_gain_for_vshunt(v_shunt_max_v: float) -> Gain:
        # Smallest range that covers expected shunt drop
        if v_shunt_max_v <= 0.040:
            return Gain.DIV_1_40MV
        elif v_shunt_max_v <= 0.080:
            return Gain.DIV_2_80MV
        elif v_shunt_max_v <= 0.160:
            return Gain.DIV_4_160MV
        else:
            return Gain.DIV_8_320MV  # up to 0.320 V full scale

    @classmethod
    def from_shunt(
        cls,
        shunt_res_ohms: float,
        max_expected_current_a: float,
        *,
        bus_voltage_range: BusVoltageRange = BusVoltageRange.RANGE_32V,
        bus_adc_resolution: ADCResolution = ADCResolution.ADCRES_12BIT_32S,
        shunt_adc_resolution: ADCResolution = ADCResolution.ADCRES_12BIT_32S,
        mode: Mode = Mode.SHUNT_AND_BUS_CONTINUOUS,
        gain: Optional[Gain] = None,
        nice_current_lsb_step_mA: Optional[float] = 0.1,
    ) -> "INA219Config":
        """
        Build INA219Config from shunt resistance and max expected current.

        Parameters:
          shunt_res_ohms: Shunt resistor value in ohms (> 0).
          max_expected_current_a: Maximum expected current in amperes (> 0).
          bus_voltage_range, bus_adc_resolution, shunt_adc_resolution, mode:
            Non-calibration fields; passed through.
          gain: Optional override for PGA gain (shunt voltage range).
          nice_current_lsb_step_mA: If set, round Current_LSB up to this step
            in mA/bit (e.g., 0.1). Set to None for exact theoretical value.

        Returns:
          INA219Config with derived gain (if not overridden), current_lsb (mA/bit),
          calibration_value (uint16), and power_lsb (W/bit).

        Raises:
          ValueError if inputs are invalid or the shunt drop exceeds 320 mV.
        """
        if shunt_res_ohms <= 0.0:
            raise ValueError("shunt_res_ohms must be > 0")
        if max_expected_current_a <= 0.0:
            raise ValueError("max_expected_current_a must be > 0")

        v_shunt_max_v = shunt_res_ohms * max_expected_current_a

        # INA219 limit is 320 mV.
        v_shunt_full_scale_v = 0.320
        if v_shunt_max_v > v_shunt_full_scale_v + 1e-12:
            max_allowed_current_a = v_shunt_full_scale_v / shunt_res_ohms
            raise ValueError(
                f"Expected shunt drop {v_shunt_max_v*1000:.1f} mV exceeds 320 mV limit. "
                f"Lower I_max to <= {max_allowed_current_a:.3f} A or reduce R_shunt."
            )

        chosen_gain = (
            gain if gain is not None else cls._select_gain_for_vshunt(v_shunt_max_v)
        )

        # Current_LSB (A/bit) ~= I_max / 32767
        exact_current_lsb_mA = (max_expected_current_a * 1000.0) / 32767.0
        if nice_current_lsb_step_mA is not None:
            current_lsb_mA = cls._round_up_to_step(
                exact_current_lsb_mA, nice_current_lsb_step_mA
            )
        else:
            current_lsb_mA = exact_current_lsb_mA

        current_lsb_A = current_lsb_mA / 1000.0
        if current_lsb_A <= 0:
            raise ValueError("Computed Current_LSB is non-positive; check inputs.")

        # Calibration: CAL = floor(0.04096 / (Current_LSB(A) * R_shunt(ohm)))
        cal_float = 0.04096 / (current_lsb_A * shunt_res_ohms)

        # If CAL would exceed 16-bit, increase Current_LSB to bring it within range.
        if cal_float > 65535:
            min_current_lsb_A = 0.04096 / (65535.0 * shunt_res_ohms)
            min_current_lsb_mA = min_current_lsb_A * 1000.0
            if nice_current_lsb_step_mA is not None:
                current_lsb_mA = cls._round_up_to_step(
                    min_current_lsb_mA, nice_current_lsb_step_mA
                )
            else:
                current_lsb_mA = min_current_lsb_mA
            current_lsb_A = current_lsb_mA / 1000.0
            cal_float = 0.04096 / (current_lsb_A * shunt_res_ohms)

        calibration_value = int(math.floor(cal_float))
        if calibration_value < 1:
            calibration_value = 1
            current_lsb_A = 0.04096 / (calibration_value * shunt_res_ohms)
            current_lsb_mA = current_lsb_A * 1000.0

        power_lsb_W_per_bit = 20.0 * current_lsb_A  # per datasheet

        return cls(
            bus_voltage_range=bus_voltage_range,
            gain=chosen_gain,
            bus_adc_resolution=bus_adc_resolution,
            shunt_adc_resolution=shunt_adc_resolution,
            mode=mode,
            current_lsb=current_lsb_mA,  # mA/bit
            calibration_value=calibration_value,  # 16-bit
            power_lsb=power_lsb_W_per_bit,  # W/bit
        )


if __name__ == "__main__":
    config = INA219Config.from_shunt(shunt_res_ohms=0.1, max_expected_current_a=3.2)
    print(config)
