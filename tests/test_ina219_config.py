import unittest

from robot_hat.data_types.config.ina219 import Gain, INA219Config


class TestINA219Config(unittest.TestCase):
    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            INA219Config.from_shunt(shunt_res_ohms=0.0, max_expected_current_a=1.0)

        with self.assertRaises(ValueError):
            INA219Config.from_shunt(shunt_res_ohms=0.1, max_expected_current_a=0.0)

    def test_shunt_drop_exceeds_320mv_raises(self):
        with self.assertRaises(ValueError) as cm:
            INA219Config.from_shunt(shunt_res_ohms=0.1, max_expected_current_a=4.0)
        self.assertIn("exceeds 320 mV", str(cm.exception))

    def test_gain_selection_boundaries(self):
        cfg = INA219Config.from_shunt(shunt_res_ohms=0.01, max_expected_current_a=4.0)
        self.assertEqual(cfg.gain, Gain.DIV_1_40MV)

        cfg = INA219Config.from_shunt(shunt_res_ohms=0.02, max_expected_current_a=4.0)
        self.assertEqual(cfg.gain, Gain.DIV_2_80MV)

        cfg = INA219Config.from_shunt(shunt_res_ohms=0.02, max_expected_current_a=8.0)
        self.assertEqual(cfg.gain, Gain.DIV_4_160MV)

        cfg = INA219Config.from_shunt(shunt_res_ohms=0.05, max_expected_current_a=6.0)
        self.assertEqual(cfg.gain, Gain.DIV_8_320MV)

    def test_override_gain_used(self):
        cfg = INA219Config.from_shunt(
            shunt_res_ohms=0.01,
            max_expected_current_a=4.0,
            gain=Gain.DIV_8_320MV,
        )
        self.assertEqual(cfg.gain, Gain.DIV_8_320MV)

    def test_default_nice_rounding_matches_example(self):
        cfg = INA219Config.from_shunt(shunt_res_ohms=0.1, max_expected_current_a=3.2)
        self.assertAlmostEqual(cfg.current_lsb, 0.1, places=9)
        self.assertEqual(cfg.calibration_value, 4096)
        expected_power_lsb = 20.0 * (0.1 / 1000.0)
        self.assertAlmostEqual(cfg.power_lsb, expected_power_lsb, places=12)
        self.assertEqual(cfg.gain, Gain.DIV_8_320MV)

    def test_exact_current_lsb_when_none(self):
        cfg = INA219Config.from_shunt(
            shunt_res_ohms=0.1,
            max_expected_current_a=3.2,
            nice_current_lsb_step_mA=None,
        )
        exact_current_lsb_mA = (3.2 * 1000.0) / 32767.0
        self.assertAlmostEqual(cfg.current_lsb, exact_current_lsb_mA, places=9)
        expected_power = 20.0 * (exact_current_lsb_mA / 1000.0)
        self.assertAlmostEqual(cfg.power_lsb, expected_power, places=12)

    def test_calibration_ceiling_enforced(self):
        cfg = INA219Config.from_shunt(
            shunt_res_ohms=0.0001,
            max_expected_current_a=1.0,
            nice_current_lsb_step_mA=None,
        )
        self.assertEqual(cfg.calibration_value, 65535)
        min_current_lsb_A = 0.04096 / (65535.0 * 0.0001)
        min_current_lsb_mA = min_current_lsb_A * 1000.0
        self.assertAlmostEqual(cfg.current_lsb, min_current_lsb_mA, places=9)
        expected_power = 20.0 * (min_current_lsb_mA / 1000.0)
        self.assertAlmostEqual(cfg.power_lsb, expected_power, places=12)


if __name__ == "__main__":
    unittest.main()
