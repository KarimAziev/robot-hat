import math
import unittest

from robot_hat.data_types.config.ina226 import ConversionTime, INA226Config, Mode


class TestINA226Config(unittest.TestCase):
    def test_from_shunt_with_expected_current(self):
        cfg = INA226Config.from_shunt(
            shunt_ohms=0.002,
            max_expected_amps=4.096,
            bus_conv_time=ConversionTime.CT_8244US,
            shunt_conv_time=ConversionTime.CT_8244US,
            mode=Mode.SHUNT_AND_BUS_CONT,
        )

        expected_current_lsb = 4.096 / INA226Config.CURRENT_LSB_FACTOR
        self.assertAlmostEqual(cfg.current_lsb, expected_current_lsb, places=12)

        expected_cal = math.floor(
            INA226Config.CALIBRATION_CONSTANT / (expected_current_lsb * 0.002)
        )
        self.assertEqual(cfg.calibration_value, expected_cal)

        self.assertAlmostEqual(cfg.power_lsb, expected_current_lsb * 25.2, places=12)

    def test_from_shunt_with_none_expected_current_uses_max_possible(self):
        cfg = INA226Config.from_shunt(
            shunt_ohms=0.002,
            max_expected_amps=None,
        )

        expected_current_lsb = (
            INA226Config.DEFAULT_SHUNT_V_MAX / 0.002
        ) / INA226Config.CURRENT_LSB_FACTOR
        self.assertAlmostEqual(cfg.current_lsb, expected_current_lsb, places=12)

        expected_cal = math.floor(
            INA226Config.CALIBRATION_CONSTANT / (expected_current_lsb * 0.002)
        )
        self.assertEqual(cfg.calibration_value, expected_cal)
        self.assertAlmostEqual(cfg.power_lsb, expected_current_lsb * 25.2, places=12)

    def test_from_shunt_raises_if_expected_exceeds_possible(self):
        shunt_ohms = 0.01
        with self.assertRaises(ValueError) as cm:
            INA226Config.from_shunt(shunt_ohms=shunt_ohms, max_expected_amps=9.0)

        self.assertIn("greater than max possible", str(cm.exception))

    def test_small_expected_triggers_calibration_cap_and_raises_lsb(self):
        shunt_ohms = 0.002
        tiny_expected = 1e-9
        cfg = INA226Config.from_shunt(
            shunt_ohms=shunt_ohms, max_expected_amps=tiny_expected
        )

        min_current_lsb = INA226Config.CALIBRATION_CONSTANT / (
            INA226Config.MAX_CALIBRATION * shunt_ohms
        )

        self.assertGreaterEqual(cfg.current_lsb, min_current_lsb - 1e-15)

        self.assertLessEqual(cfg.calibration_value, INA226Config.MAX_CALIBRATION)

        self.assertGreaterEqual(cfg.calibration_value, 1)

    def test_invalid_shunt_ohms_raises(self):
        with self.assertRaises(ValueError):
            INA226Config.from_shunt(shunt_ohms=0.0, max_expected_amps=1.0)


if __name__ == "__main__":
    unittest.main()
