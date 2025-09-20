from dataclasses import dataclass


@dataclass(frozen=True)
class SH3001Config:
    ACC_XL: int = 0x00
    CHIP_ID: int = 0x0F

    # accelerometer configuration
    ODR_500HZ: int = 0x01
    ACC_RANGE_2G: int = 0x05
    ACC_ODRX025: int = 0x20  # defined cutoff frequency
    ACC_FILTER_EN: int = 0x00
    ACC_CONF0: int = 0x22
    ACC_CONF1: int = 0x23
    ACC_CONF2: int = 0x25
    ACC_CONF3: int = 0x26

    # gyroscope configuration
    GYRO_RANGE_2000: int = 0x06
    GYRO_ODRX00: int = 0x00
    GYRO_FILTER_EN: int = 0x10
    GYRO_CONF0: int = 0x28
    GYRO_CONF1: int = 0x29
    GYRO_CONF3: int = 0x8F
    GYRO_CONF4: int = 0x9F
    GYRO_CONF5: int = 0xAF
    GYRO_CONF2: int = 0x2B

    # temperature configuration
    TEMP_ODR_63: int = 0x30
    TEMP_EN: int = 0x80
    TEMP_CONF0: int = 0x20
