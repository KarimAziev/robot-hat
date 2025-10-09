import unittest
from typing import List, Optional, Sequence, cast

from robot_hat.data_types.config.ina226 import INA226Config
from robot_hat.drivers.adc.INA226 import INA226
from robot_hat.interfaces.smbus_abc import SMBusABC

REG_CONFIG = 0x00
REG_SHUNTVOLTAGE = 0x01
REG_BUSVOLTAGE = 0x02
REG_POWER = 0x03
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05


def _to_be_bytes_16(value: int) -> List[int]:
    """Return big-endian 2-byte list for a 16-bit integer."""
    return [(value >> 8) & 0xFF, value & 0xFF]


class MockBus:
    def __init__(self, read_responses=None):
        self.read_responses = dict(read_responses or {})
        self.writes = []
        self.closed = False

    def write_i2c_block_data(
        self,
        i2c_addr: int,
        register: int,
        data: Sequence[int],
        _: Optional[bool] = None,
    ) -> None:
        self.writes.append((i2c_addr, register, list(data)))

    def read_i2c_block_data(
        self, i2c_addr: int, register: int, length: int, _: Optional[bool] = None
    ) -> List[int]:
        key = (i2c_addr, register, length)
        if key not in self.read_responses:
            raise KeyError(
                f"No read response registered for addr=0x{i2c_addr:02X}, register=0x{register:02X}, len={length}"
            )
        data = self.read_responses[key]
        if len(data) != length:
            raise ValueError("Registered response length mismatch")
        return list(data)

    def set_read(
        self, address: int, register: int, length: int, data: List[int]
    ) -> None:
        self.read_responses[(address, register, length)] = list(data)

    def close(self) -> None:
        self.closed = True


class TestINA226(unittest.TestCase):
    ADDR = 0x40

    def test_init_writes_calibration_and_config(self):
        cfg = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=2.0)

        mock_bus = MockBus()
        dev = INA226(bus=cast(SMBusABC, mock_bus), address=self.ADDR, config=cfg)

        self.assertGreaterEqual(len(mock_bus.writes), 2)

        cal_writes = [w for w in mock_bus.writes if w[1] == REG_CALIBRATION]
        self.assertTrue(cal_writes, "Calibration register was not written")
        addr0, _, data0 = cal_writes[0]
        self.assertEqual(addr0, self.ADDR)
        self.assertEqual(data0, _to_be_bytes_16(cfg.calibration_value))

        cfg_writes = [w for w in mock_bus.writes if w[1] == REG_CONFIG]
        self.assertTrue(cfg_writes, "Configuration register was not written")
        _, _, cfg_data = cfg_writes[0]
        written_cfg_val = (cfg_data[0] << 8) | cfg_data[1]
        expected_cfg_val = (
            (cfg.avg_mode.value << 9)
            | (cfg.bus_conv_time.value << 6)
            | (cfg.shunt_conv_time.value << 3)
            | (cfg.mode.value)
            | (1 << 14)
        )
        self.assertEqual(written_cfg_val, expected_cfg_val)

        dev.close()

    def test_get_shunt_voltage_signed_and_units(self):
        cfg = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=1.0)

        raw_signed = -100
        raw_16 = raw_signed & 0xFFFF
        mock = MockBus()
        mock.set_read(self.ADDR, REG_SHUNTVOLTAGE, 2, _to_be_bytes_16(raw_16))

        dev = INA226(bus=cast(SMBusABC, mock), address=self.ADDR, config=cfg)

        shunt_mv = dev.get_shunt_voltage_mv()
        expected_mv = raw_signed * INA226Config.SHUNT_LSB_MV
        self.assertAlmostEqual(shunt_mv, expected_mv, places=9)

        dev.close()

    def test_get_bus_voltage_v_scaling(self):
        cfg = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=1.0)

        raw_bus = 30000
        mock = MockBus()
        mock.set_read(self.ADDR, REG_BUSVOLTAGE, 2, _to_be_bytes_16(raw_bus))

        dev = INA226(bus=cast(SMBusABC, mock), address=self.ADDR, config=cfg)

        bus_v = dev.get_bus_voltage_v()
        expected_v = raw_bus * (INA226Config.BUS_LSB_MV / 1000.0)
        self.assertAlmostEqual(bus_v, expected_v, places=9)

        dev.close()

    def test_get_current_and_power_and_calibration_refresh(self):
        cfg = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=2.0)

        raw_current = 1000
        raw_power = 200
        mock = MockBus()
        mock.set_read(self.ADDR, REG_CURRENT, 2, _to_be_bytes_16(raw_current & 0xFFFF))
        mock.set_read(self.ADDR, REG_POWER, 2, _to_be_bytes_16(raw_power & 0xFFFF))

        dev = INA226(bus=cast(SMBusABC, mock), address=self.ADDR, config=cfg)

        current_ma = dev.get_current_ma()
        expected_current_ma = (
            (raw_current if raw_current < 0x8000 else raw_current - 0x10000)
            * cfg.current_lsb
            * 1000.0
        )
        self.assertAlmostEqual(current_ma, expected_current_ma, places=9)

        cal_writes_before = [w for w in mock.writes if w[1] == REG_CALIBRATION]
        before_count = len(cal_writes_before)

        power_mw = dev.get_power_mw()
        expected_power_mw = (
            (raw_power if raw_power < 0x8000 else raw_power - 0x10000)
            * cfg.power_lsb
            * 1000.0
        )
        self.assertAlmostEqual(power_mw, expected_power_mw, places=9)

        cal_writes_after = [w for w in mock.writes if w[1] == REG_CALIBRATION]
        self.assertGreaterEqual(len(cal_writes_after), max(1, before_count + 1))

        dev.close()

    def test_update_config_rewrites_registers_and_close(self):
        cfg1 = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=1.0)
        cfg2 = INA226Config.from_shunt(shunt_ohms=0.01, max_expected_amps=2.0)

        mock = MockBus()
        dev = INA226(bus=cast(SMBusABC, mock), address=self.ADDR, config=cfg1)

        mock.writes.clear()
        dev.update_config(cfg2)

        self.assertGreaterEqual(len(mock.writes), 2)
        _, reg0, data0 = mock.writes[0]
        self.assertEqual(reg0, REG_CALIBRATION)
        self.assertEqual(data0, _to_be_bytes_16(cfg2.calibration_value))

        cfg_writes = [w for w in mock.writes if w[1] == REG_CONFIG]
        self.assertTrue(cfg_writes)
        _, _, cfg_data = cfg_writes[0]
        written_cfg_val = (cfg_data[0] << 8) | cfg_data[1]
        expected_cfg_val = (
            (cfg2.avg_mode.value << 9)
            | (cfg2.bus_conv_time.value << 6)
            | (cfg2.shunt_conv_time.value << 3)
            | (cfg2.mode.value)
            | (1 << 14)
        )
        self.assertEqual(written_cfg_val, expected_cfg_val)

        dev.close()
        self.assertEqual(mock.closed, dev.own_bus)


if __name__ == "__main__":
    unittest.main()
