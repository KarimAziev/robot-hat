import unittest
from typing import cast

from robot_hat.data_types.bus import BusType
from robot_hat.drivers.pwm import sunfounder_pwm as sf_module
from robot_hat.drivers.pwm.sunfounder_pwm import SunfounderPWM
from robot_hat.exceptions import InvalidChannelNumber


class FakeBus:
    """A simple fake SMBus-like object to capture write_word_data calls."""

    def __init__(self):
        self.calls = []
        self.closed = False

    def write_word_data(self, address, reg, data):
        self.calls.append((address, reg, data))

    def close(self):
        self.closed = True


def pack16(value: int) -> int:
    """Pack a 16-bit value the same way SunfounderPWM._i2c_write does."""
    value_h = (value >> 8) & 0xFF
    value_l = value & 0xFF
    return (value_l << 8) + value_h


class TestSunfounderPWM(unittest.TestCase):
    def setUp(self):
        self.bus = FakeBus()
        self.address = 0x14
        self.pwm = SunfounderPWM(address=self.address, bus=cast(BusType, self.bus))

    def test_init_writes_timer_registers(self):
        calls = list(self.bus.calls)
        self.assertEqual(len(calls), sf_module.NUM_TIMERS * 2)

        idx = 0
        for timer in range(sf_module.NUM_TIMERS):
            if timer < 4:
                reg_psc = self.pwm.REG_PSC + timer  # type: ignore
                reg_arr = self.pwm.REG_ARR + timer  # type: ignore
            else:
                reg_psc = self.pwm.REG_PSC2 + (timer - 4)  # type: ignore
                reg_arr = self.pwm.REG_ARR2 + (timer - 4)  # type: ignore

            psc_value = self.pwm._prescaler - 1  # type: ignore
            arr_value = self.pwm._arr  # type: ignore

            addr, reg, data = calls[idx]
            self.assertEqual(addr, self.address)
            self.assertEqual(reg, reg_psc)
            self.assertEqual(data, pack16(psc_value))
            idx += 1

            addr, reg, data = calls[idx]
            self.assertEqual(addr, self.address)
            self.assertEqual(reg, reg_arr)
            self.assertEqual(data, pack16(arr_value))
            idx += 1

    def test_set_pwm_freq_adjusts_and_writes(self):
        prev_calls = len(self.bus.calls)
        self.pwm.set_pwm_freq(100)
        new_calls = len(self.bus.calls)
        self.assertEqual(new_calls - prev_calls, sf_module.NUM_TIMERS * 2)
        self.assertEqual(self.pwm._freq, 100)  # type: ignore
        self.assertIsInstance(self.pwm._prescaler, int)  # type: ignore
        self.assertIsInstance(self.pwm._arr, int)  # type: ignore
        self.assertGreater(self.pwm._prescaler, 0)  # type: ignore
        self.assertGreater(self.pwm._arr, 0)  # type: ignore

    def test_set_servo_pulse_writes_correct_register_and_value(self):
        self.bus.calls.clear()
        channel = 3
        pulse_us = 1500

        expected_ticks = int(
            round((float(pulse_us) / float(self.pwm._frame_width)) * self.pwm._arr)  # type: ignore
        )
        self.pwm.set_servo_pulse(channel, pulse_us)

        self.assertEqual(len(self.bus.calls), 1)
        addr, reg, data = self.bus.calls[0]
        self.assertEqual(addr, self.address)
        self.assertEqual(reg, self.pwm.REG_CHN + channel)  # type: ignore
        self.assertEqual(data, pack16(expected_ticks))

    def test_set_servo_pulse_clamps_negative_and_overflow(self):
        self.bus.calls.clear()
        channel = 0
        self.pwm.set_servo_pulse(channel, -1000)
        _, _, data = self.bus.calls[-1]
        self.assertEqual(data, pack16(0))

        self.bus.calls.clear()
        self.pwm.set_servo_pulse(channel, self.pwm._frame_width * 10)  # type: ignore
        _, _, data = self.bus.calls[-1]
        self.assertEqual(data, pack16(self.pwm._arr))  # type: ignore

    def test_set_servo_pulse_invalid_channel_raises(self):
        with self.assertRaises(InvalidChannelNumber):
            self.pwm.set_servo_pulse(-1, 1000)
        with self.assertRaises(InvalidChannelNumber):
            self.pwm.set_servo_pulse(20, 1000)

    def test_set_pwm_duty_cycle_value_error_on_invalid(self):
        with self.assertRaises(ValueError):
            self.pwm.set_pwm_duty_cycle(0, -10)
        with self.assertRaises(ValueError):
            self.pwm.set_pwm_duty_cycle(0, 200)

    def test_set_pwm_duty_cycle_writes_expected_value(self):
        self.bus.calls.clear()
        channel = 2
        duty = 25
        expected_val = int((duty / 100.0) * self.pwm._arr)  # type: ignore
        self.pwm.set_pwm_duty_cycle(channel, duty)

        self.assertEqual(len(self.bus.calls), 1)
        addr, reg, data = self.bus.calls[0]
        self.assertEqual(addr, self.address)
        self.assertEqual(reg, self.pwm.REG_CHN + channel)  # type: ignore
        self.assertEqual(data, pack16(expected_val))


if __name__ == "__main__":
    unittest.main()
