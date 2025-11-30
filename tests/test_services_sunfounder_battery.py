import unittest
from unittest.mock import MagicMock, patch

from robot_hat.data_types import BatteryMetrics
from robot_hat.services.battery.sunfounder_battery import Battery as SunfounderBattery
from robot_hat.services.battery.sunfounder_battery import ADC


def _fake_adc_init(self, channel, address, *args, **kwargs):
    normalized = ADC._normalize_channel(channel)
    channel_reg = ADC._channel_to_register(normalized)
    self._channel_index = normalized
    self._channel_reg = channel_reg
    self.channel = channel_reg
    self._own_bus = False
    self._smbus = None


class TestSunfounderBattery(unittest.TestCase):
    def setUp(self) -> None:
        self.patcher = patch(
            "robot_hat.services.battery.sunfounder_battery.ADC.__init__",
            new=_fake_adc_init,
        )
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()

    def test_current_requires_configuration(self) -> None:
        battery = SunfounderBattery()

        with self.assertRaises(NotImplementedError):
            battery.get_battery_current()

    def test_current_with_configuration(self) -> None:
        battery = SunfounderBattery(current_channel="A3", sense_resistance_ohms=0.01)
        battery.read_voltage_channel = MagicMock(return_value=0.048)

        current = battery.get_battery_current()

        expected_channel = ADC._normalize_channel("A3")
        battery.read_voltage_channel.assert_called_once_with(expected_channel)
        self.assertEqual(current, 4.8)

    def test_missing_pair_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            SunfounderBattery(current_channel="A1")

        with self.assertRaises(ValueError):
            SunfounderBattery(sense_resistance_ohms=0.01)

    def test_invalid_resistance_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            SunfounderBattery(current_channel="A1", sense_resistance_ohms=0)

    def test_metrics_requires_current_configuration(self) -> None:
        battery = SunfounderBattery()
        battery.get_battery_voltage = MagicMock(return_value=11.1)

        with self.assertRaises(NotImplementedError):
            battery.get_battery_metrics()

    def test_metrics_returns_dataclass_when_configured(self) -> None:
        battery = SunfounderBattery(current_channel="A3", sense_resistance_ohms=0.01)
        battery.get_battery_voltage = MagicMock(return_value=10.5)
        battery.get_battery_current = MagicMock(return_value=4.2)

        metrics = battery.get_battery_metrics()

        battery.get_battery_voltage.assert_called_once()
        battery.get_battery_current.assert_called_once()
        self.assertEqual(metrics, BatteryMetrics(voltage=10.5, current=4.2))


if __name__ == "__main__":
    unittest.main()
