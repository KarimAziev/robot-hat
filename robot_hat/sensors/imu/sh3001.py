import logging
import math
import time
from typing import Callable, ClassVar, List, Optional

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.sh3001 import SH3001Config
from robot_hat.data_types.imu import IMUSample, RawIMUSample
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.i2c.i2c_manager import I2C
from robot_hat.interfaces.imu_abc import IMUABC

_log = logging.getLogger(__name__)

_STANDARD_GRAVITY_MPS2 = 9.80665
_DEGREES_TO_RADIANS = math.pi / 180.0


class SH3001(I2C, IMUABC):
    SH3001_ADDRESS: ClassVar[int] = 0x36  # 7bit: 011 0111

    """
    /******************************************************************
    *	SH3001 Registers Macro Definitions
    ******************************************************************/
    """
    SH3001_ACC_XL = 0x00
    SH3001_ACC_XH = 0x01
    SH3001_ACC_YL = 0x02
    SH3001_ACC_YH = 0x03
    SH3001_ACC_ZL = 0x04
    SH3001_ACC_ZH = 0x05
    SH3001_GYRO_XL = 0x06
    SH3001_GYRO_XH = 0x07
    SH3001_GYRO_YL = 0x08
    SH3001_GYRO_YH = 0x09
    SH3001_GYRO_ZL = 0x0A
    SH3001_GYRO_ZH = 0x0B
    SH3001_TEMP_ZL = 0x0C
    SH3001_TEMP_ZH = 0x0D
    SH3001_CHIP_ID_REGISTER = 0x0F
    SH3001_CHIP_ID_VALUE = 0x61
    SH3001_INT_STA0 = 0x10
    SH3001_INT_STA1 = 0x11
    SH3001_INT_STA2 = 0x12
    SH3001_INT_STA3 = 0x14
    SH3001_INT_STA4 = 0x15
    SH3001_FIFO_STA0 = 0x16
    SH3001_FIFO_STA1 = 0x17
    SH3001_FIFO_DATA = 0x18
    SH3001_TEMP_CONF0 = 0x20
    SH3001_TEMP_CONF1 = 0x21

    SH3001_ACC_CONF0 = 0x22  # accelerometer config 0x22-0x26
    SH3001_ACC_CONF1 = 0x23
    SH3001_ACC_CONF2 = 0x25
    SH3001_ACC_CONF3 = 0x26

    SH3001_GYRO_CONF0 = 0x28  # gyroscope config 0x28-0x2B
    SH3001_GYRO_CONF1 = 0x29
    SH3001_GYRO_CONF2 = 0x2B

    SH3001_SPI_CONF = 0x32
    SH3001_FIFO_CONF0 = 0x35
    SH3001_FIFO_CONF1 = 0x36
    SH3001_FIFO_CONF2 = 0x37
    SH3001_FIFO_CONF3 = 0x38
    SH3001_FIFO_CONF4 = 0x39
    SH3001_MI2C_CONF0 = 0x3A
    SH3001_MI2C_CONF1 = 0x3B
    SH3001_MI2C_CMD0 = 0x3C
    SH3001_MI2C_CMD1 = 0x3D
    SH3001_MI2C_WR = 0x3E
    SH3001_MI2C_RD = 0x3F
    SH3001_INT_ENABLE0 = 0x40
    SH3001_INT_ENABLE1 = 0x41
    SH3001_INT_CONF = 0x44
    SH3001_INT_LIMIT = 0x45
    SH3001_ORIEN_INTCONF0 = 0x46
    SH3001_ORIEN_INTCONF1 = 0x47
    SH3001_ORIEN_INT_LOW = 0x48
    SH3001_ORIEN_INT_HIGH = 0x49
    SH3001_ORIEN_INT_SLOPE_LOW = 0x4A
    SH3001_ORIEN_INT_SLOPE_HIGH = 0x4B
    SH3001_ORIEN_INT_HYST_LOW = 0x4C
    SH3001_ORIEN_INT_HYST_HIGH = 0x4D
    SH3001_FLAT_INT_CONF = 0x4E
    SH3001_ACT_INACT_INT_CONF = 0x4F
    SH3001_ACT_INACT_INT_LINK = 0x50
    SH3001_TAP_INT_THRESHOLD = 0x51
    SH3001_TAP_INT_DURATION = 0x52
    SH3001_TAP_INT_LATENCY = 0x53
    SH3001_DTAP_INT_WINDOW = 0x54
    SH3001_ACT_INT_THRESHOLD = 0x55
    SH3001_ACT_INT_TIME = 0x56
    SH3001_INACT_INT_THRESHOLDL = 0x57
    SH3001_INACT_INT_TIME = 0x58
    SH3001_HIGHLOW_G_INT_CONF = 0x59
    SH3001_HIGHG_INT_THRESHOLD = 0x5A
    SH3001_HIGHG_INT_TIME = 0x5B
    SH3001_LOWG_INT_THRESHOLD = 0x5C
    SH3001_LOWG_INT_TIME = 0x5D
    SH3001_FREEFALL_INT_THRES = 0x5E
    SH3001_FREEFALL_INT_TIME = 0x5F
    SH3001_INT_PIN_MAP0 = 0x79
    SH3001_INT_PIN_MAP1 = 0x7A
    SH3001_INACT_INT_THRESHOLDM = 0x7B
    SH3001_INACT_INT_THRESHOLDH = 0x7C
    SH3001_INACT_INT_1G_REFL = 0x7D
    SH3001_INACT_INT_1G_REFH = 0x7E
    SH3001_SPI_REG_ACCESS = 0x7F
    SH3001_GYRO_CONF3 = 0x8F
    SH3001_GYRO_CONF4 = 0x9F
    SH3001_GYRO_CONF5 = 0xAF
    SH3001_AUX_I2C_CONF = 0xFD
    """
    /******************************************************************
    *	ACC Config Macro Definitions
    ******************************************************************/
    """
    SH3001_ODR_1000HZ = 0x00
    SH3001_ODR_500HZ = 0x01
    SH3001_ODR_250HZ = 0x02
    SH3001_ODR_125HZ = 0x03
    SH3001_ODR_63HZ = 0x04
    SH3001_ODR_31HZ = 0x05
    SH3001_ODR_16HZ = 0x06
    SH3001_ODR_2000HZ = 0x08
    SH3001_ODR_4000HZ = 0x09
    SH3001_ODR_8000HZ = 0x0A
    SH3001_ODR_16000HZ = 0x0B
    SH3001_ODR_32000HZ = 0x0C

    SH3001_ACC_RANGE_16G = 0x02
    SH3001_ACC_RANGE_8G = 0x03
    SH3001_ACC_RANGE_4G = 0x04
    SH3001_ACC_RANGE_2G = 0x05

    SH3001_ACC_ODRX040 = 0x00
    SH3001_ACC_ODRX025 = 0x20
    SH3001_ACC_ODRX011 = 0x40
    SH3001_ACC_ODRX004 = 0x60

    SH3001_ACC_FILTER_EN = 0x00
    SH3001_ACC_FILTER_DIS = 0x80
    """
    /******************************************************************
    *	GYRO Config Macro Definitions
    ******************************************************************/
    """
    SH3001_GYRO_RANGE_125 = 0x02
    SH3001_GYRO_RANGE_250 = 0x03
    SH3001_GYRO_RANGE_500 = 0x04
    SH3001_GYRO_RANGE_1000 = 0x05
    SH3001_GYRO_RANGE_2000 = 0x06

    SH3001_GYRO_ODRX00 = 0x00
    SH3001_GYRO_ODRX01 = 0x04
    SH3001_GYRO_ODRX02 = 0x08
    SH3001_GYRO_ODRX03 = 0x0C

    SH3001_GYRO_FILTER_EN = 0x00
    SH3001_GYRO_FILTER_DIS = 0x10
    """
    /******************************************************************
    *	Temperature Config Macro Definitions
    ******************************************************************/
    """
    SH3001_TEMP_ODR_500 = 0x00
    SH3001_TEMP_ODR_250 = 0x10
    SH3001_TEMP_ODR_125 = 0x20
    SH3001_TEMP_ODR_63 = 0x30

    SH3001_TEMP_EN = 0x80
    SH3001_TEMP_DIS = 0x00
    """
    /******************************************************************
    *	INT Config Macro Definitions
    ******************************************************************/
    """
    SH3001_INT_LOWG = 0x8000
    SH3001_INT_HIGHG = 0x4000
    SH3001_INT_INACT = 0x2000
    SH3001_INT_ACT = 0x1000
    SH3001_INT_DOUBLE_TAP = 0x0800
    SH3001_INT_TAP = 0x0400
    SH3001_INT_FLAT = 0x0200
    SH3001_INT_ORIENTATION = 0x0100
    SH3001_INT_FIFO_GYRO = 0x0010
    SH3001_INT_GYRO_READY = 0x0008
    SH3001_INT_ACC_FIFO = 0x0004
    SH3001_INT_ACC_READY = 0x0002
    SH3001_INT_FREE_FALL = 0x0001
    SH3001_INT_UP_DOWN_Z = 0x0040

    SH3001_INT_ENABLE = 0x01
    SH3001_INT_DISABLE = 0x00

    SH3001_INT_MAP_INT1 = 0x01
    SH3001_INT_MAP_INT = 0x00

    SH3001_INT_LEVEL_LOW = 0x80
    SH3001_INT_LEVEL_HIGH = 0x7F
    SH3001_INT_NO_LATCH = 0x40
    SH3001_INT_LATCH = 0xBF
    SH3001_INT_CLEAR_ANY = 0x10
    SH3001_INT_CLEAR_STATUS = 0xEF
    SH3001_INT_INT1_NORMAL = 0x04
    SH3001_INT_INT1_OD = 0xFB
    SH3001_INT_INT_NORMAL = 0x01
    SH3001_INT_INT_OD = 0xFE
    """
    /******************************************************************
    *	Orientation Blocking Config Macro Definitions
    ******************************************************************/
    """
    SH3001_ORIENT_BLOCK_MODE0 = 0x00
    SH3001_ORIENT_BLOCK_MODE1 = 0x04
    SH3001_ORIENT_BLOCK_MODE2 = 0x08
    SH3001_ORIENT_BLOCK_MODE3 = 0x0C

    SH3001_ORIENT_SYMM = 0x00
    SH3001_ORIENT_HIGH_ASYMM = 0x01
    SH3001_ORIENT_LOW_ASYMM = 0x02
    """
    /******************************************************************
    *	Flat Time Config Macro Definitions
    ******************************************************************/
    """
    SH3001_FLAT_TIME_500MS = 0x40
    SH3001_FLAT_TIME_1000MS = 0x80
    SH3001_FLAT_TIME_2000MS = 0xC0
    """
    /******************************************************************
    *	ACT and INACT Int Config Macro Definitions
    ******************************************************************/
    """
    SH3001_ACT_AC_MODE = 0x80
    SH3001_ACT_DC_MODE = 0x00
    SH3001_ACT_X_INT_EN = 0x40
    SH3001_ACT_X_INT_DIS = 0x00
    SH3001_ACT_Y_INT_EN = 0x20
    SH3001_ACT_Y_INT_DIS = 0x00
    SH3001_ACT_Z_INT_EN = 0x10
    SH3001_ACT_Z_INT_DIS = 0x00

    SH3001_INACT_AC_MODE = 0x08
    SH3001_INACT_DC_MODE = 0x00
    SH3001_INACT_X_INT_EN = 0x04
    SH3001_INACT_X_INT_DIS = 0x00
    SH3001_INACT_Y_INT_EN = 0x02
    SH3001_INACT_Y_INT_DIS = 0x00
    SH3001_INACT_Z_INT_EN = 0x01
    SH3001_INACT_Z_INT_DIS = 0x00

    SH3001_LINK_PRE_STA = 0x01
    SH3001_LINK_PRE_STA_NO = 0x00
    """
    /******************************************************************
    *	TAP Int Config Macro Definitions
    ******************************************************************/
    """
    SH3001_TAP_X_INT_EN = 0x08
    SH3001_TAP_X_INT_DIS = 0x00
    SH3001_TAP_Y_INT_EN = 0x04
    SH3001_TAP_Y_INT_DIS = 0x00
    SH3001_TAP_Z_INT_EN = 0x02
    SH3001_TAP_Z_INT_DIS = 0x00
    """
    /******************************************************************
    *	HIGHG Int Config Macro Definitions
    ******************************************************************/
    """

    SH3001_HIGHG_ALL_INT_EN = 0x80
    SH3001_HIGHG_ALL_INT_DIS = 0x00
    SH3001_HIGHG_X_INT_EN = 0x40
    SH3001_HIGHG_X_INT_DIS = 0x00
    SH3001_HIGHG_Y_INT_EN = 0x20
    SH3001_HIGHG_Y_INT_DIS = 0x00
    SH3001_HIGHG_Z_INT_EN = 0x10
    SH3001_HIGHG_Z_INT_DIS = 0x00
    """
    /******************************************************************
    *	LOWG Int Config Macro Definitions
    ******************************************************************/
    """
    SH3001_LOWG_ALL_INT_EN = 0x01
    SH3001_LOWG_ALL_INT_DIS = 0x00
    """
    /******************************************************************
    *	SPI Interface Config Macro Definitions
    ******************************************************************/
    """
    SH3001_SPI_3_WIRE = 0x01
    SH3001_SPI_4_WIRE = 0x00
    """
    /******************************************************************
    *	FIFO Config Macro Definitions
    ******************************************************************/
    """
    SH3001_FIFO_MODE_DIS = 0x00
    SH3001_FIFO_MODE_FIFO = 0x01
    SH3001_FIFO_MODE_STREAM = 0x02
    SH3001_FIFO_MODE_TRIGGER = 0x03

    SH3001_FIFO_ACC_DOWNS_EN = 0x80
    SH3001_FIFO_ACC_DOWNS_DIS = 0x00
    SH3001_FIFO_GYRO_DOWNS_EN = 0x08
    SH3001_FIFO_GYRO_DOWNS_DIS = 0x00

    SH3001_FIFO_FREQ_X1_2 = 0x00
    SH3001_FIFO_FREQ_X1_4 = 0x01
    SH3001_FIFO_FREQ_X1_8 = 0x02
    SH3001_FIFO_FREQ_X1_16 = 0x03
    SH3001_FIFO_FREQ_X1_32 = 0x04
    SH3001_FIFO_FREQ_X1_64 = 0x05
    SH3001_FIFO_FREQ_X1_128 = 0x06
    SH3001_FIFO_FREQ_X1_256 = 0x07

    SH3001_FIFO_EXT_Z_EN = 0x2000
    SH3001_FIFO_EXT_Y_EN = 0x1000
    SH3001_FIFO_EXT_X_EN = 0x0080
    SH3001_FIFO_TEMPERATURE_EN = 0x0040
    SH3001_FIFO_GYRO_Z_EN = 0x0020
    SH3001_FIFO_GYRO_Y_EN = 0x0010
    SH3001_FIFO_GYRO_X_EN = 0x0008
    SH3001_FIFO_ACC_Z_EN = 0x0004
    SH3001_FIFO_ACC_Y_EN = 0x0002
    SH3001_FIFO_ACC_X_EN = 0x0001
    SH3001_FIFO_ALL_DIS = 0x0000
    """
    /******************************************************************
    *	AUX I2C Config Macro Definitions
    ******************************************************************/
    """
    SH3001_MI2C_NORMAL_MODE = 0x00
    SH3001_MI2C_BYPASS_MODE = 0x01

    SH3001_MI2C_READ_ODR_200HZ = 0x00
    SH3001_MI2C_READ_ODR_100HZ = 0x10
    SH3001_MI2C_READ_ODR_50HZ = 0x20
    SH3001_MI2C_READ_ODR_25HZ = 0x30

    SH3001_MI2C_FAIL = 0x20
    SH3001_MI2C_SUCCESS = 0x10

    SH3001_MI2C_READ_MODE_AUTO = 0x40
    SH3001_MI2C_READ_MODE_MANUAL = 0x00
    """
    /******************************************************************
    *	Other Macro Definitions
    ******************************************************************/
    """
    SH3001_TRUE = 0
    SH3001_FALSE = 1

    SH3001_NORMAL_MODE = 0x00
    SH3001_SLEEP_MODE = 0x01
    SH3001_POWERDOWN_MODE = 0x02

    def __init__(
        self,
        address=SH3001_ADDRESS,
        bus: BusType = 1,
        config: Optional[SH3001Config] = None,
        monotonic_ns: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        """
        Initialize the SH3001 instance with the given I2C address and bus.
        """
        super().__init__(address=address, bus=bus)
        self.config: SH3001Config = config if config is not None else SH3001Config()
        self._monotonic_ns = monotonic_ns

    @staticmethod
    def bytes_to_int(msb: int, lsb: int) -> int:
        """
        Convert two bytes (MSB and LSB) to a signed integer using big-endian format.
        If MSB does not indicate a negative value, returns the positive integer.
        """
        value = (msb << 8) | lsb
        return value - 0x10000 if value & 0x8000 else value

    def read_raw_sample(self) -> RawIMUSample:
        """Read signed ADC counts for diagnostics and calibration."""

        reg_data = self.mem_read(12, self.SH3001_ACC_XL)
        if len(reg_data) != 12:
            raise IMUReadError(f"SH3001 returned {len(reg_data)} of 12 sample bytes")
        return RawIMUSample(
            accelerometer_counts=(
                self.bytes_to_int(reg_data[1], reg_data[0]),
                self.bytes_to_int(reg_data[3], reg_data[2]),
                self.bytes_to_int(reg_data[5], reg_data[4]),
            ),
            gyroscope_counts=(
                self.bytes_to_int(reg_data[7], reg_data[6]),
                self.bytes_to_int(reg_data[9], reg_data[8]),
                self.bytes_to_int(reg_data[11], reg_data[10]),
            ),
            timestamp_monotonic_ns=self._monotonic_ns(),
        )

    def read_sample(self) -> IMUSample:
        """Read one immutable, timestamped sample in SI units."""

        raw = self.read_raw_sample()
        acceleration_scale = (
            _STANDARD_GRAVITY_MPS2 / self.config.accelerometer_lsb_per_g
        )
        angular_velocity_scale = _DEGREES_TO_RADIANS / self.config.gyroscope_lsb_per_dps
        acceleration = raw.accelerometer_counts
        angular_velocity = raw.gyroscope_counts
        return IMUSample(
            acceleration_mps2=(
                acceleration[0] * acceleration_scale,
                acceleration[1] * acceleration_scale,
                acceleration[2] * acceleration_scale,
            ),
            angular_velocity_radps=(
                angular_velocity[0] * angular_velocity_scale,
                angular_velocity[1] * angular_velocity_scale,
                angular_velocity[2] * angular_velocity_scale,
            ),
            timestamp_monotonic_ns=raw.timestamp_monotonic_ns,
        )

    def initialize(self) -> None:
        """
        Initialize and configure the sensor. Checks if the sensor's CHIP_ID is valid.
        Configures the accelerometer, gyroscope, and temperature sensor.

        Raises IMUInitializationError if the CHIP_ID is not as expected.
        """
        for _ in range(3):
            reg_data = self.mem_read(1, self.SH3001_CHIP_ID_REGISTER)
            if reg_data and reg_data[0] == self.SH3001_CHIP_ID_VALUE:
                break
        else:
            raise IMUInitializationError(
                "SH3001 chip ID mismatch: expected 0x61 at register 0x0F"
            )

        self._configure_accelerometer(
            output_data_rate=self.SH3001_ODR_500HZ,
            range_data=self.config.accelerometer_range_register,
            cut_off_freq=self.SH3001_ACC_ODRX025,
            filter_enable=self.SH3001_ACC_FILTER_EN,
        )
        self._configure_gyroscope(
            output_data_rate=self.SH3001_ODR_500HZ,
            range_x=self.config.gyroscope_range_register,
            range_y=self.config.gyroscope_range_register,
            range_z=self.config.gyroscope_range_register,
            cut_off_freq=self.SH3001_GYRO_ODRX00,
            filter_enable=self.SH3001_GYRO_FILTER_EN,
        )
        self._configure_temperature(
            output_data_rate=self.SH3001_TEMP_ODR_63,
            enable=self.SH3001_TEMP_EN,
        )

    def _configure_accelerometer(
        self,
        output_data_rate: int,
        range_data: int,
        cut_off_freq: int,
        filter_enable: int,
    ) -> None:
        """
        Configure the accelerometer with the specified output data rate,
        range, cutoff frequency, and filter settings.

        Reads current register settings, enables the digital filter,
        and applies configuration.
        """
        reg_data: Optional[List[int]] = self.mem_read(1, self.SH3001_ACC_CONF0)
        if reg_data:
            reg_data[0] |= 0x01
            self.mem_write(reg_data, self.SH3001_ACC_CONF0)

        self.mem_write(output_data_rate, self.SH3001_ACC_CONF1)
        self.mem_write(range_data, self.SH3001_ACC_CONF2)
        reg_data = self.mem_read(1, self.SH3001_ACC_CONF3)
        if reg_data:
            reg_data[0] &= 0x17
            reg_data[0] |= cut_off_freq | filter_enable
            self.mem_write(reg_data, self.SH3001_ACC_CONF3)

    def _configure_gyroscope(
        self,
        output_data_rate: int,
        range_x: int,
        range_y: int,
        range_z: int,
        cut_off_freq: int,
        filter_enable: int,
    ) -> None:
        """
        Configure the gyroscope with the specified output data rate and range settings
        for the X, Y, and Z axes, along with cutoff frequency and filter options.
        """
        reg_data: Optional[List[int]] = self.mem_read(1, self.SH3001_GYRO_CONF0)
        if reg_data:
            reg_data[0] |= 0x01
            self.mem_write(reg_data, self.SH3001_GYRO_CONF0)

        self.mem_write(output_data_rate, self.SH3001_GYRO_CONF1)
        self.mem_write(range_x, self.SH3001_GYRO_CONF3)
        self.mem_write(range_y, self.SH3001_GYRO_CONF4)
        self.mem_write(range_z, self.SH3001_GYRO_CONF5)
        reg_data = self.mem_read(1, self.SH3001_GYRO_CONF2)
        if reg_data:
            reg_data[0] &= 0xE3
            reg_data[0] |= cut_off_freq | filter_enable
            self.mem_write(reg_data, self.SH3001_GYRO_CONF2)

    def _configure_temperature(self, output_data_rate: int, enable: int) -> None:
        """
        Configure the temperature sensor by setting the output data rate and enabling
        or disabling the temperature measurement.
        """
        reg_data: Optional[List[int]] = self.mem_read(1, self.SH3001_TEMP_CONF0)
        if reg_data:
            reg_data[0] &= 0x4F
            reg_data[0] |= output_data_rate | enable
            self.mem_write(reg_data, self.SH3001_TEMP_CONF0)
            _ = self.mem_read(1, self.SH3001_TEMP_CONF0)
