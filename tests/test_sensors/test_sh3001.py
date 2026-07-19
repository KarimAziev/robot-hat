import logging
import math
import unittest
from typing import List, cast
from unittest.mock import Mock, call

from robot_hat.data_types.config.sh3001 import SH3001Config
from robot_hat.exceptions import IMUInitializationError, IMUReadError
from robot_hat.sensors.imu.sh3001 import SH3001


class TestSH3001(unittest.TestCase):
    def make_instance(self):
        """
        Create an SH3001 instance without invoking I2C.__init__ which would try to open SMBus.
        The returned object has internal attributes set so destructor/close won't raise, and
        mem_read/mem_write to be mocked by tests.
        """
        inst = object.__new__(SH3001)
        inst.config = SH3001Config()
        inst._monotonic_ns = Mock(return_value=123_456_789)

        inst._address = 0x36
        inst._own_bus = False

        inst.mem_read = Mock()
        inst.mem_write = Mock()
        return inst

    def test_bytes_to_int_positive(self):
        msb = 0x01
        lsb = 0x02
        res = SH3001.bytes_to_int(msb, lsb)
        self.assertEqual(res, (msb << 8) | lsb)

    def test_bytes_to_int_negative(self):
        msb = 0xFF
        lsb = 0xFE
        res = SH3001.bytes_to_int(msb, lsb)
        self.assertEqual(res, -2)

    def test_read_raw_sample_success(self):
        inst = self.make_instance()

        reg_data = [
            0x02,
            0x01,
            0x04,
            0x03,
            0x06,
            0x05,
            0x08,
            0x07,
            0x0A,
            0x09,
            0x0C,
            0x0B,
        ]
        cast(Mock, inst.mem_read).return_value = reg_data

        sample = inst.read_raw_sample()

        self.assertEqual(sample.accelerometer_counts, (258, 772, 1286))
        self.assertEqual(sample.gyroscope_counts, (1800, 2314, 2828))
        self.assertEqual(sample.timestamp_monotonic_ns, 123_456_789)
        cast(Mock, inst.mem_read).assert_called_once_with(12, inst.SH3001_ACC_XL)

    def test_read_sample_converts_configured_ranges_to_si_units(self):
        inst = self.make_instance()

        def little_endian(value: int) -> List[int]:
            unsigned = value & 0xFFFF
            return [unsigned & 0xFF, unsigned >> 8]

        cast(Mock, inst.mem_read).return_value = (
            little_endian(16384)
            + little_endian(-16384)
            + little_endian(8192)
            + little_endian(1640)
            + little_endian(-1640)
            + little_endian(0)
        )

        sample = inst.read_sample()

        self.assertAlmostEqual(sample.acceleration_mps2[0], 9.80665)
        self.assertAlmostEqual(sample.acceleration_mps2[1], -9.80665)
        self.assertAlmostEqual(sample.acceleration_mps2[2], 9.80665 / 2)
        self.assertAlmostEqual(sample.angular_velocity_radps[0], math.radians(100))
        self.assertAlmostEqual(sample.angular_velocity_radps[1], math.radians(-100))
        self.assertEqual(sample.angular_velocity_radps[2], 0.0)

    def test_read_raw_sample_rejects_incomplete_data(self):
        inst = self.make_instance()
        cast(Mock, inst.mem_read).return_value = [0] * 11

        with self.assertRaisesRegex(IMUReadError, "11 of 12"):
            inst.read_raw_sample()

    def test_read_raw_sample_exceptions_propagate(self):
        inst = self.make_instance()

        cast(Mock, inst.mem_read).side_effect = TimeoutError("timeout")
        with self.assertRaises(TimeoutError):
            inst.read_raw_sample()

        cast(Mock, inst.mem_read).side_effect = OSError("os error")
        with self.assertRaises(OSError):
            inst.read_raw_sample()

        cast(Mock, inst.mem_read).side_effect = Exception("generic")
        with self.assertRaises(Exception):
            inst.read_raw_sample()

    def test_initialize_success_calls_configure_and_reset(self):
        inst = self.make_instance()
        cfg = inst.config

        def mem_read_side_effect(length: int, memaddr: int) -> List[int]:
            logging.debug("mem_read=%s", length)
            if memaddr == inst.SH3001_CHIP_ID_REGISTER:
                return [inst.SH3001_CHIP_ID_VALUE]
            return [0]

        cast(Mock, inst.mem_read).side_effect = mem_read_side_effect

        inst._configure_accelerometer = Mock()
        inst._configure_gyroscope = Mock()
        inst._configure_temperature = Mock()

        inst.initialize()

        cast(Mock, inst.mem_read).assert_any_call(1, inst.SH3001_CHIP_ID_REGISTER)
        inst._configure_accelerometer.assert_called_once_with(
            output_data_rate=inst.SH3001_ODR_500HZ,
            range_data=cfg.accelerometer_range_register,
            cut_off_freq=inst.SH3001_ACC_ODRX025,
            filter_enable=inst.SH3001_ACC_FILTER_EN,
        )
        inst._configure_gyroscope.assert_called_once_with(
            output_data_rate=inst.SH3001_ODR_500HZ,
            range_x=cfg.gyroscope_range_register,
            range_y=cfg.gyroscope_range_register,
            range_z=cfg.gyroscope_range_register,
            cut_off_freq=inst.SH3001_GYRO_ODRX00,
            filter_enable=inst.SH3001_GYRO_FILTER_EN,
        )
        inst._configure_temperature.assert_called_once_with(
            output_data_rate=inst.SH3001_TEMP_ODR_63,
            enable=inst.SH3001_TEMP_EN,
        )

    def test_initialize_chip_id_failure_raises(self):
        inst = self.make_instance()
        cast(Mock, inst.mem_read).return_value = [0x00]

        with self.assertRaises(IMUInitializationError):
            inst.initialize()
        self.assertEqual(cast(Mock, inst.mem_read).call_count, 3)

    def test_configure_accelerometer_reads_and_writes(self):
        inst = self.make_instance()
        cfg = inst.config

        def mem_read_side_effect(length: int, memaddr: int) -> List[int]:
            logging.debug("mem_read=%s", length)
            if memaddr == inst.SH3001_ACC_CONF0:
                return [0x00]
            if memaddr == inst.SH3001_ACC_CONF3:
                return [0xFF]
            return [0x00]

        cast(Mock, inst.mem_read).side_effect = mem_read_side_effect
        cast(Mock, inst.mem_write).reset_mock()

        inst._configure_accelerometer(
            output_data_rate=inst.SH3001_ODR_500HZ,
            range_data=cfg.accelerometer_range_register,
            cut_off_freq=inst.SH3001_ACC_ODRX025,
            filter_enable=inst.SH3001_ACC_FILTER_EN,
        )

        expected_first = call([0x01], inst.SH3001_ACC_CONF0)
        expected_second = call(inst.SH3001_ODR_500HZ, inst.SH3001_ACC_CONF1)
        expected_third = call(
            cfg.accelerometer_range_register,
            inst.SH3001_ACC_CONF2,
        )
        expected_fourth = call([0x37], inst.SH3001_ACC_CONF3)

        self.assertIn(expected_first, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_second, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_third, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_fourth, cast(Mock, inst.mem_write).call_args_list)


if __name__ == "__main__":
    unittest.main()
