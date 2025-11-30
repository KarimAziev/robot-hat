import unittest

from robot_hat.data_types import BatteryMetrics
from robot_hat.services.battery.ina219_battery import Battery as INA219Battery
from robot_hat.services.battery.ina226_battery import Battery as INA226Battery
from robot_hat.services.battery.ina260_battery import Battery as INA260Battery


class TestBatteryMetricsAggregates(unittest.TestCase):
    def test_ina219_metrics_dataclass(self) -> None:
        battery = object.__new__(INA219Battery)
        battery.get_battery_voltage = lambda: 12.34  # type: ignore[attr-defined]
        battery.get_battery_current = lambda: 3.21  # type: ignore[attr-defined]

        metrics = battery.get_battery_metrics()

        self.assertEqual(metrics, BatteryMetrics(voltage=12.34, current=3.21))

    def test_ina226_metrics_dataclass(self) -> None:
        battery = object.__new__(INA226Battery)
        battery.get_battery_voltage = lambda: 11.5  # type: ignore[attr-defined]
        battery.get_battery_current = lambda: 4.8  # type: ignore[attr-defined]

        metrics = battery.get_battery_metrics()

        self.assertEqual(metrics, BatteryMetrics(voltage=11.5, current=4.8))

    def test_ina260_metrics_dataclass(self) -> None:
        battery = object.__new__(INA260Battery)
        battery.get_battery_voltage = lambda: 9.87  # type: ignore[attr-defined]
        battery.get_battery_current = lambda: 2.34  # type: ignore[attr-defined]

        metrics = battery.get_battery_metrics()

        self.assertEqual(metrics, BatteryMetrics(voltage=9.87, current=2.34))


if __name__ == "__main__":
    unittest.main()
