import logging
import unittest
from typing import List, cast
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.sh3001 import SH3001Config
from robot_hat.exceptions import IMUInitializationError
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

    def test_read_sensor_data_success(self):
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

        accel, gyro = inst.read_sensor_data()

        self.assertEqual(accel, [258, 772, 1286])
        self.assertEqual(gyro, [1800, 2314, 2828])
        cast(Mock, inst.mem_read).assert_called_once_with(12, inst.config.ACC_XL)

    def test_read_sensor_data_exceptions_propagate(self):
        inst = self.make_instance()

        cast(Mock, inst.mem_read).side_effect = TimeoutError("timeout")
        with self.assertRaises(TimeoutError):
            inst.read_sensor_data()

        cast(Mock, inst.mem_read).side_effect = OSError("os error")
        with self.assertRaises(OSError):
            inst.read_sensor_data()

        cast(Mock, inst.mem_read).side_effect = Exception("generic")
        with self.assertRaises(Exception):
            inst.read_sensor_data()

    def test_initialize_success_calls_configure_and_reset(self):
        inst = self.make_instance()
        cfg = inst.config

        def mem_read_side_effect(length: int, memaddr: int) -> List[int]:
            logging.debug("mem_read=%s", length)
            if memaddr == cfg.CHIP_ID:
                return [cfg.CHIP_ID]
            return [0]

        cast(Mock, inst.mem_read).side_effect = mem_read_side_effect

        inst._reset = Mock()
        inst._configure_accelerometer = Mock()
        inst._configure_gyroscope = Mock()
        inst._configure_temperature = Mock()

        inst.initialize()

        cast(Mock, inst.mem_read).assert_any_call(1, cfg.CHIP_ID)
        inst._reset.assert_called_once()
        inst._configure_accelerometer.assert_called_once_with(
            output_data_rate=cfg.ODR_500HZ,
            range_data=cfg.ACC_RANGE_2G,
            cut_off_freq=cfg.ACC_ODRX025,
            filter_enable=cfg.ACC_FILTER_EN,
        )
        inst._configure_gyroscope.assert_called_once_with(
            output_data_rate=cfg.ODR_500HZ,
            range_x=cfg.GYRO_RANGE_2000,
            range_y=cfg.GYRO_RANGE_2000,
            range_z=cfg.GYRO_RANGE_2000,
            cut_off_freq=cfg.GYRO_ODRX00,
            filter_enable=cfg.GYRO_FILTER_EN,
        )
        inst._configure_temperature.assert_called_once_with(
            output_data_rate=cfg.TEMP_ODR_63, enable=cfg.TEMP_EN
        )

    def test_initialize_chip_id_failure_raises(self):
        inst = self.make_instance()
        cast(Mock, inst.mem_read).return_value = [0x00]

        with self.assertRaises(IMUInitializationError):
            inst.initialize()
        self.assertGreaterEqual(cast(Mock, inst.mem_read).call_count, 1)
        self.assertLessEqual(cast(Mock, inst.mem_read).call_count, 3)

    @patch("time.sleep", return_value=None)
    def test_reset_writes_expected_sequence(self, _):
        inst = self.make_instance()

        cast(Mock, inst.mem_write).reset_mock()
        inst._reset()

        expected_calls = [
            call(0x73, inst.address),
            call(0x02, inst.address),
            call(0xC1, inst.address),
            call(0xC2, inst.address),
            call(0x00, inst.address),
            call(0x18, inst.address),
            call(0x00, inst.address),
        ]

        self.assertEqual(cast(Mock, inst.mem_write).call_args_list, expected_calls)

    def test_configure_accelerometer_reads_and_writes(self):
        inst = self.make_instance()
        cfg = inst.config

        def mem_read_side_effect(length: int, memaddr: int) -> List[int]:
            logging.debug("mem_read=%s", length)
            if memaddr == cfg.ACC_CONF0:
                return [0x00]
            if memaddr == cfg.ACC_CONF3:
                return [0xFF]
            return [0x00]

        cast(Mock, inst.mem_read).side_effect = mem_read_side_effect
        cast(Mock, inst.mem_write).reset_mock()

        inst._configure_accelerometer(
            output_data_rate=cfg.ODR_500HZ,
            range_data=cfg.ACC_RANGE_2G,
            cut_off_freq=cfg.ACC_ODRX025,
            filter_enable=cfg.ACC_FILTER_EN,
        )

        expected_first = call([0x01], cfg.ACC_CONF0)
        expected_second = call(cfg.ODR_500HZ, cfg.ACC_CONF1)
        expected_third = call(cfg.ACC_RANGE_2G, cfg.ACC_CONF2)
        expected_fourth = call([0x37], cfg.ACC_CONF3)

        self.assertIn(expected_first, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_second, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_third, cast(Mock, inst.mem_write).call_args_list)
        self.assertIn(expected_fourth, cast(Mock, inst.mem_write).call_args_list)


if __name__ == "__main__":
    unittest.main()
