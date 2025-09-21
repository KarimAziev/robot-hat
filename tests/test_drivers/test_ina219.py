import unittest
from unittest.mock import Mock, call

from robot_hat.data_types.config.ina219 import INA219Config
from robot_hat.drivers.adc.INA219 import (
    INA219,
    REG_BUSVOLTAGE,
    REG_CALIBRATION,
    REG_CONFIG,
    REG_CURRENT,
    REG_POWER,
    REG_SHUNTVOLTAGE,
)


class TestINA219(unittest.TestCase):
    def setUp(self):
        self.bus = Mock()
        self.bus.write_i2c_block_data.return_value = None

    def _expected_bytes(self, value: int):
        return [(value >> 8) & 0xFF, value & 0xFF]

    def test_init_writes_calibration_and_config(self):
        config = INA219Config()
        ina = INA219(bus=self.bus, address=0x41, config=config)

        self.assertEqual(self.bus.write_i2c_block_data.call_count, 2)

        cal_value = config.calibration_value
        expected_cal = self._expected_bytes(cal_value)
        first_call = self.bus.write_i2c_block_data.call_args_list[0]
        self.assertEqual(first_call, call(0x41, REG_CALIBRATION, expected_cal))

        cfg_val = (
            (config.bus_voltage_range.value << 13)
            | (config.gain.value << 11)
            | (config.bus_adc_resolution.value << 7)
            | (config.shunt_adc_resolution.value << 3)
            | (config.mode.value)
        )
        expected_cfg = self._expected_bytes(cfg_val)
        second_call = self.bus.write_i2c_block_data.call_args_list[1]
        self.assertEqual(second_call, call(0x41, REG_CONFIG, expected_cfg))

        ina.close()

    def test_read_register_success_and_error(self):
        self.bus.read_i2c_block_data.return_value = [0x12, 0x34]
        ina = INA219(bus=self.bus, address=0x50, config=INA219Config())

        val = ina._read_register(0x10)
        self.assertEqual(val, 0x1234)
        self.bus.read_i2c_block_data.assert_called_with(0x50, 0x10, 2)

        self.bus.read_i2c_block_data.side_effect = OSError("bus read error")
        with self.assertRaises(OSError):
            ina._read_register(0x10)

    def test_write_register_error_propagates(self):
        ina = INA219(bus=self.bus, address=0x42, config=INA219Config())
        self.bus.write_i2c_block_data.side_effect = OSError("write fail")
        with self.assertRaises(OSError):
            ina._write_register(REG_CONFIG, 0xABCD)

    def test_twos_complement(self):
        self.assertEqual(INA219._twos_complement(0x007F, 16), 0x007F)
        self.assertEqual(INA219._twos_complement(0xFFFF, 16), -1)
        self.assertEqual(INA219._twos_complement(0xFFFE, 16), -2)

    def test_get_shunt_voltage_mv_and_bus_voltage_and_current_and_power(self):
        def read_side_effect(addr, reg, length):
            if reg == REG_SHUNTVOLTAGE:
                return [0x00, 0x64]
            elif reg == REG_BUSVOLTAGE:
                return [0x01, 0x00]
            elif reg == REG_CURRENT:
                return [0x00, 0x32]
            elif reg == REG_POWER:
                return [0x00, 0x32]
            else:
                return [0x00, 0x00]

        self.bus.read_i2c_block_data.side_effect = read_side_effect

        ina = INA219(bus=self.bus, address=0x41, config=INA219Config())

        self.bus.write_i2c_block_data.reset_mock()
        self.bus.read_i2c_block_data.reset_mock()

        shunt_mv = ina.get_shunt_voltage_mv()
        self.bus.write_i2c_block_data.assert_called_once_with(
            0x41, REG_CALIBRATION, self._expected_bytes(ina._cal_value)
        )
        self.assertAlmostEqual(shunt_mv, 1.0, places=6)

        bus_v = ina.get_bus_voltage_v()
        self.assertAlmostEqual(bus_v, 0.128, places=6)

        current_ma = ina.get_current_ma()
        self.assertAlmostEqual(current_ma, 50 * ina._current_lsb, places=6)

        self.bus.write_i2c_block_data.reset_mock()
        power_w = ina.get_power_w()
        self.assertAlmostEqual(power_w, 50 * ina._power_lsb, places=6)
        self.bus.write_i2c_block_data.assert_called_once_with(
            0x41, REG_CALIBRATION, self._expected_bytes(ina._cal_value)
        )

    def test_update_config_writes_new_calibration(self):
        ina = INA219(bus=self.bus, address=0x41, config=INA219Config())

        self.bus.write_i2c_block_data.reset_mock()

        new_cfg = INA219Config(
            current_lsb=0.5,
            calibration_value=0x04D2,
            power_lsb=0.01,
        )

        ina.update_config(new_cfg)

        self.assertGreaterEqual(self.bus.write_i2c_block_data.call_count, 2)
        first = self.bus.write_i2c_block_data.call_args_list[0]
        self.assertEqual(
            first,
            call(
                0x41, REG_CALIBRATION, self._expected_bytes(new_cfg.calibration_value)
            ),
        )

        self.assertEqual(ina._cal_value, new_cfg.calibration_value)
        self.assertEqual(ina._current_lsb, new_cfg.current_lsb)
        self.assertEqual(ina._power_lsb, new_cfg.power_lsb)

    def test_close_does_not_close_injected_bus(self):
        ina = INA219(bus=self.bus, address=0x41, config=INA219Config())
        self.assertFalse(ina.own_bus)
        ina.close()
        self.bus.close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
