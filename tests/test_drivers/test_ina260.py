import unittest
from unittest.mock import Mock, call, patch

from robot_hat.data_types.config.ina260 import AveragingCount, INA260Config
from robot_hat.drivers.adc.INA260 import (
    INA260,
    REG_ALERT_LIMIT,
    REG_BUSVOLTAGE,
    REG_CONFIG,
    REG_CURRENT,
    REG_DIE_ID,
    REG_MANUFACTURER_ID,
    REG_MASK_ENABLE,
    REG_POWER,
)


class TestINA260Driver(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = Mock()
        self.bus.write_i2c_block_data.return_value = None

    def _expected_bytes(self, value: int) -> list[int]:
        return [(value >> 8) & 0xFF, value & 0xFF]

    def test_init_writes_config_only_when_no_alerts(self) -> None:
        config = INA260Config()
        INA260(bus=self.bus, address=0x40, config=config)

        self.bus.write_i2c_block_data.assert_called_once_with(
            0x40, REG_CONFIG, self._expected_bytes(config.to_register_value())
        )

    def test_init_writes_alert_registers_when_configured(self) -> None:
        config = INA260Config(alert_mask=0x1234, alert_limit=0x5678)
        INA260(bus=self.bus, address=0x41, config=config)

        expected_calls = [
            call(0x41, REG_CONFIG, self._expected_bytes(config.to_register_value())),
            call(0x41, REG_MASK_ENABLE, self._expected_bytes(0x1234)),
            call(0x41, REG_ALERT_LIMIT, self._expected_bytes(0x5678)),
        ]

        self.assertEqual(self.bus.write_i2c_block_data.call_args_list, expected_calls)

    def test_measurement_conversions(self) -> None:
        def read_side_effect(address, reg, length):
            if reg == REG_CURRENT:
                return [0xFF, 0x38]  # -200 in twos complement -> -250 mA
            if reg == REG_BUSVOLTAGE:
                return [0x01, 0x00]  # 0x0100 -> 256 * 1.25mV = 0.32 V
            if reg == REG_POWER:
                return [0x00, 0x64]  # 100 * 10mW = 1000 mW
            raise AssertionError(f"Unexpected register read: 0x{reg:02X}")

        self.bus.read_i2c_block_data.side_effect = read_side_effect

        ina = INA260(bus=self.bus, address=0x40, config=INA260Config())

        current_ma = ina.get_current_ma()
        self.assertAlmostEqual(current_ma, -250.0, places=6)

        voltage_v = ina.get_bus_voltage_v()
        self.assertAlmostEqual(voltage_v, 0.32, places=6)

        power_mw = ina.get_power_mw()
        self.assertAlmostEqual(power_mw, 1000.0, places=6)

        shunt_mv = ina.get_shunt_voltage_mv()
        self.assertAlmostEqual(
            shunt_mv, current_ma * ina.config.shunt_resistance_ohms, places=6
        )

    def test_update_config_rewrites_registers(self) -> None:
        ina = INA260(bus=self.bus, address=0x40, config=INA260Config())
        self.bus.write_i2c_block_data.reset_mock()

        new_config = INA260Config(
            averaging_count=AveragingCount.COUNT_64,
            alert_mask=0x0001,
            alert_limit=0x0002,
        )

        ina.update_config(new_config)

        expected_calls = [
            call(
                0x40, REG_CONFIG, self._expected_bytes(new_config.to_register_value())
            ),
            call(0x40, REG_MASK_ENABLE, self._expected_bytes(0x0001)),
            call(0x40, REG_ALERT_LIMIT, self._expected_bytes(0x0002)),
        ]
        self.assertEqual(self.bus.write_i2c_block_data.call_args_list, expected_calls)

        self.assertEqual(ina.config, new_config)

    def test_validate_device_signature_success(self) -> None:
        config = INA260Config()

        def read_side_effect(address, reg, length):
            if reg == REG_MANUFACTURER_ID:
                return [0x54, 0x49]
            if reg == REG_DIE_ID:
                return [0x02, 0x60]
            return [0x00, 0x00]

        self.bus.read_i2c_block_data.side_effect = read_side_effect

        INA260(
            bus=self.bus,
            address=0x40,
            config=config,
            validate_device_id=True,
        )

    def test_validate_device_signature_failure(self) -> None:
        self.bus.read_i2c_block_data.return_value = [0x00, 0x00]

        with self.assertRaises(RuntimeError):
            INA260(
                bus=self.bus,
                address=0x40,
                config=INA260Config(),
                validate_device_id=True,
            )

    def test_close_does_not_close_injected_bus(self) -> None:
        ina = INA260(bus=self.bus, address=0x40, config=INA260Config())
        ina.close()
        self.bus.close.assert_not_called()

    def test_close_closes_owned_bus(self) -> None:
        fake_bus = Mock()
        with patch("robot_hat.i2c.i2c_bus.I2CBus", return_value=fake_bus):
            ina = INA260(bus=1, address=0x40, config=INA260Config())
            self.assertTrue(ina.own_bus)
        ina.close()
        fake_bus.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
