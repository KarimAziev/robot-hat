import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class AvgMode(IntEnum):
    AVG_1 = 0
    AVG_4 = 1
    AVG_16 = 2
    AVG_64 = 3
    AVG_128 = 4
    AVG_256 = 5
    AVG_512 = 6
    AVG_1024 = 7


class ConversionTime(IntEnum):
    CT_140US = 0
    CT_204US = 1
    CT_332US = 2
    CT_588US = 3
    CT_1100US = 4
    CT_2116US = 5
    CT_4156US = 6
    CT_8244US = 7


class Mode(IntEnum):
    POWERDOWN = 0
    SHUNT_TRIG = 1
    BUS_TRIG = 2
    SHUNT_AND_BUS_TRIG = 3
    ADC_OFF = 4
    SHUNT_CONT = 5
    BUS_CONT = 6
    SHUNT_AND_BUS_CONT = 7


@dataclass
class INA226Config:
    """
    Config dataclass for INA226.

    Fields:
      avg_mode: averaging (0..7)
      bus_conv_time: bus conversion time
      shunt_conv_time: shunt conversion time
      mode: operating mode bits
      shunt_ohms: shunt resistance in ohms
      max_expected_amps: Optional maximum expected current in A. If provided,
                         current LSB is derived from this. If None, the
                         device limits are used to compute LSB.
    Derived/calculated fields:
      current_lsb: A/bit (used for current register scaling)
      calibration_value: integer written to calibration register (16-bit)
      power_lsb: W/bit (power register scaling)
    """

    avg_mode: AvgMode = field(default=AvgMode.AVG_1)
    bus_conv_time: ConversionTime = field(default=ConversionTime.CT_8244US)
    shunt_conv_time: ConversionTime = field(default=ConversionTime.CT_8244US)
    mode: Mode = field(default=Mode.SHUNT_AND_BUS_CONT)

    shunt_ohms: float = field(default=0.002)
    max_expected_amps: Optional[float] = field(default=None)

    current_lsb: float = field(default=0.0)
    calibration_value: int = field(default=0)
    power_lsb: float = field(default=0.0)

    BUS_RANGE_V = 40.96
    DEFAULT_SHUNT_V_MAX = 0.08192
    SHUNT_LSB_MV = 0.0025
    BUS_LSB_MV = 1.25
    CALIBRATION_CONSTANT = 0.00512
    MAX_CALIBRATION = 0x7FFF
    CURRENT_LSB_FACTOR = 32768.0

    @classmethod
    def from_shunt(
        cls,
        shunt_ohms: float,
        max_expected_amps: Optional[float],
        *,
        avg_mode: AvgMode = AvgMode.AVG_1,
        bus_conv_time: ConversionTime = ConversionTime.CT_8244US,
        shunt_conv_time: ConversionTime = ConversionTime.CT_8244US,
        mode: Mode = Mode.SHUNT_AND_BUS_CONT,
        shunt_volts_max: float = DEFAULT_SHUNT_V_MAX,
    ) -> "INA226Config":
        """
        Build INA226Config deriving calibration values from shunt resistor and expected current.

        - shunt_ohms: Rshunt in ohms (>0)
        - max_expected_amps: optional expected max current in A
        - shunt_volts_max: maximum shunt voltage used to compute max possible current
        """
        if shunt_ohms <= 0.0:
            raise ValueError("shunt_ohms must be > 0")
        cfg = cls(
            avg_mode=avg_mode,
            bus_conv_time=bus_conv_time,
            shunt_conv_time=shunt_conv_time,
            mode=mode,
            shunt_ohms=shunt_ohms,
            max_expected_amps=max_expected_amps,
        )

        max_possible_amps = shunt_volts_max / shunt_ohms

        if max_expected_amps is not None:
            if max_expected_amps > round(max_possible_amps, 3):
                raise ValueError(
                    f"Expected current {max_expected_amps:.3f}A is greater than max possible "
                    f"{max_possible_amps:.3f}A (shunt Vmax {shunt_volts_max:.6f} V)"
                )
            base_current_lsb = max_expected_amps / cls.CURRENT_LSB_FACTOR
        else:
            base_current_lsb = max_possible_amps / cls.CURRENT_LSB_FACTOR

        calibration_float = cls.CALIBRATION_CONSTANT / (base_current_lsb * shunt_ohms)

        if calibration_float > cls.MAX_CALIBRATION:
            min_current_lsb = cls.CALIBRATION_CONSTANT / (
                cls.MAX_CALIBRATION * shunt_ohms
            )
            base_current_lsb = max(base_current_lsb, min_current_lsb)
            calibration_float = cls.CALIBRATION_CONSTANT / (
                base_current_lsb * shunt_ohms
            )

        calibration_value = int(math.floor(calibration_float))
        if calibration_value < 1:
            calibration_value = 1
            base_current_lsb = cls.CALIBRATION_CONSTANT / (
                calibration_value * shunt_ohms
            )

        power_lsb = base_current_lsb * 25.2

        cfg.current_lsb = base_current_lsb
        cfg.calibration_value = calibration_value
        cfg.power_lsb = power_lsb

        return cfg


if __name__ == "__main__":
    # Example: derive a config for a 2 mOhm shunt that will see up to 10 A
    cfg = INA226Config.from_shunt(
        shunt_ohms=0.002,
        max_expected_amps=10.0,
        avg_mode=AvgMode.AVG_16,
        bus_conv_time=ConversionTime.CT_8244US,
        shunt_conv_time=ConversionTime.CT_8244US,
        mode=Mode.SHUNT_AND_BUS_CONT,
    )

    print("Derived INA226 configuration:")
    print(cfg)
    print("Current LSB (A/bit):", cfg.current_lsb)
    print("Calibration register value:", cfg.calibration_value)
    print("Power LSB (W/bit):", cfg.power_lsb)
