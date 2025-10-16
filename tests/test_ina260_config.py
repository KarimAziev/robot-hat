import unittest

from robot_hat.data_types.config.ina260 import (
    AveragingCount,
    ConversionTime,
    INA260Config,
    Mode,
)


class TestINA260Config(unittest.TestCase):
    def test_to_register_value_combines_bits(self) -> None:
        cfg = INA260Config(
            averaging_count=AveragingCount.COUNT_64,
            voltage_conversion_time=ConversionTime.TIME_2_116_MS,
            current_conversion_time=ConversionTime.TIME_4_156_MS,
            mode=Mode.CURRENT_CONTINUOUS,
            reset_on_init=True,
        )

        value = cfg.to_register_value()

        self.assertEqual(value >> 15, 1)
        self.assertEqual((value >> 9) & 0x07, AveragingCount.COUNT_64)
        self.assertEqual((value >> 6) & 0x07, ConversionTime.TIME_2_116_MS)
        self.assertEqual((value >> 3) & 0x07, ConversionTime.TIME_4_156_MS)
        self.assertEqual(value & 0x07, Mode.CURRENT_CONTINUOUS)

    def test_copy_with_overrides_selected_fields(self) -> None:
        base = INA260Config()
        mutated = base.copy_with(
            averaging_count=AveragingCount.COUNT_16,
            alert_mask=0x1234,
            alert_limit=0x5678,
            shunt_resistance_ohms=0.0015,
            reset_on_init=True,
        )

        self.assertEqual(mutated.averaging_count, AveragingCount.COUNT_16)
        self.assertEqual(mutated.alert_mask, 0x1234)
        self.assertEqual(mutated.alert_limit, 0x5678)
        self.assertAlmostEqual(mutated.shunt_resistance_ohms, 0.0015)
        self.assertTrue(mutated.reset_on_init)
        self.assertEqual(mutated.voltage_conversion_time, base.voltage_conversion_time)

    def test_invalid_shunt_resistance_raises(self) -> None:
        with self.assertRaises(ValueError):
            INA260Config(shunt_resistance_ohms=0.0)

    def test_invalid_alert_values_raise(self) -> None:
        with self.assertRaises(ValueError):
            INA260Config(alert_mask=0x1_0000)
        with self.assertRaises(ValueError):
            INA260Config(alert_limit=-1)


if __name__ == "__main__":
    unittest.main()
