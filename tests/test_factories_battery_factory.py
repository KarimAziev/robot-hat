import unittest
from unittest.mock import MagicMock, patch

from robot_hat.data_types.config.battery import (
    INA219BatteryConfig,
    INA226BatteryConfig,
    INA260BatteryConfig,
    SunfounderBatteryConfig,
)
from robot_hat.factories.battery_factory import BatteryFactory


class TestBatteryFactory(unittest.TestCase):
    @patch("robot_hat.factories.battery_factory.INA219Battery")
    def test_create_ina219_battery(self, mock_battery):
        bus = MagicMock()
        config = INA219BatteryConfig(bus=bus, address=0x41, sensor_config=MagicMock())

        result = BatteryFactory.create_battery(config, validate_device_id=True)

        mock_battery.assert_called_once_with(
            bus=bus,
            address=0x41,
            config=config.sensor_config,
            validate_device_id=True,
        )
        self.assertEqual(result, mock_battery.return_value)

    @patch("robot_hat.factories.battery_factory.INA226Battery")
    def test_create_ina226_battery(self, mock_battery):
        config = INA226BatteryConfig(bus=2, address=0x45, sensor_config=None)

        BatteryFactory.create_battery(config)

        mock_battery.assert_called_once_with(bus=2, address=0x45, config=None)

    @patch("robot_hat.factories.battery_factory.INA260Battery")
    def test_create_ina260_battery_forwards_kwargs(self, mock_battery):
        sensor_config = MagicMock()
        config = INA260BatteryConfig(bus=3, address=0x40, sensor_config=sensor_config)

        BatteryFactory.create_battery(config, some_flag=False)

        mock_battery.assert_called_once_with(
            bus=3,
            address=0x40,
            config=sensor_config,
            some_flag=False,
        )

    @patch("robot_hat.factories.battery_factory.SunfounderBattery")
    def test_create_sunfounder_battery(self, mock_battery):
        config = SunfounderBatteryConfig(channel="A2", address=[0x14])

        BatteryFactory.create_battery(config)

        mock_battery.assert_called_once_with(channel="A2", address=[0x14])

    def test_unsupported_config_type_raises(self):
        class CustomConfig:
            pass

        with self.assertRaises(TypeError):
            BatteryFactory.create_battery(CustomConfig())  # type: ignore


if __name__ == "__main__":
    unittest.main()
