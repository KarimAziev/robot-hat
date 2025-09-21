import math
import unittest
from unittest.mock import Mock, call, patch

from robot_hat import PCA9685
from robot_hat.drivers.pwm.pca9685 import PCA9685Register
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC


class TestPCA9685(unittest.TestCase):
    def _patch_pwm_driver_init(self, mock_bus):

        def fake_init(self, *args, **kwargs):
            if "bus" in kwargs:
                bus = kwargs["bus"]
            elif len(args) >= 1:
                bus = args[0]
            else:
                bus = None

            if "address" in kwargs:
                address = kwargs["address"]
            elif len(args) >= 2:
                address = args[1]
            else:
                address = None

            self._bus = bus
            self._address = address

        return patch.object(PWMDriverABC, "__init__", new=fake_init)

    def test_init_writes_mode1_zero(self):
        mock_bus = Mock()
        address = 0x40

        with self._patch_pwm_driver_init(mock_bus):
            _ = PCA9685(address=address, bus=mock_bus)

        mock_bus.write_byte_data.assert_called_with(
            address, int(PCA9685Register.MODE1), 0x00
        )

    def test_set_pwm_writes_four_registers(self):
        mock_bus = Mock()
        address = 0x40

        with self._patch_pwm_driver_init(mock_bus):
            pwm = PCA9685(address=address, bus=mock_bus)

        mock_bus.write_byte_data.reset_mock()

        channel = 3
        on = 0x123
        off = 0x456

        pwm.set_pwm(channel, on, off)  # type: ignore

        base_addr = int(PCA9685Register.LED0_ON_L) + 4 * channel
        expected_calls = [
            call(address, base_addr, on & 0xFF),
            call(address, base_addr + 1, on >> 8),
            call(address, base_addr + 2, off & 0xFF),
            call(address, base_addr + 3, off >> 8),
        ]
        mock_bus.write_byte_data.assert_has_calls(expected_calls, any_order=False)
        self.assertEqual(mock_bus.write_byte_data.call_count, 4)

    def test_set_pwm_freq_writes_prescale_and_modes(self):
        mock_bus = Mock()
        address = 0x40
        mock_bus.read_byte_data.return_value = 0x00

        with self._patch_pwm_driver_init(mock_bus):
            pwm = PCA9685(address=address, bus=mock_bus)

        mock_bus.write_byte_data.reset_mock()

        freq = 50
        prescaleval = 25000000.0
        prescaleval /= pwm._period  # type: ignore
        prescaleval /= float(freq)
        prescaleval -= 1.0
        expected_prescale = int(math.floor(prescaleval + 0.5))

        with patch("robot_hat.drivers.pwm.pca9685.time.sleep", return_value=None):
            pwm.set_pwm_freq(freq)

        mock_bus.read_byte_data.assert_called_with(address, int(PCA9685Register.MODE1))

        expected_calls = [
            call(address, int(PCA9685Register.MODE1), (0x00 & 0x7F) | 0x10),
            call(address, int(PCA9685Register.PRESCALE), expected_prescale),
            call(address, int(PCA9685Register.MODE1), 0x00),
            call(address, int(PCA9685Register.MODE1), 0x00 | 0x80),
        ]
        mock_bus.write_byte_data.assert_has_calls(expected_calls, any_order=False)

    def test_set_servo_pulse_and_set_pwm_duty_cycle(self):
        mock_bus = Mock()
        address = 0x40

        with self._patch_pwm_driver_init(mock_bus):
            pwm = PCA9685(address=address, bus=mock_bus)

        mock_bus.write_byte_data.reset_mock()

        channel = 0
        pulse_us = 1000
        expected_off = int(pulse_us * pwm._period / pwm._frame_width)  # type: ignore
        pwm.set_servo_pulse(channel, pulse_us)

        base_addr = int(PCA9685Register.LED0_ON_L) + 4 * channel
        expected_calls = [
            call(address, base_addr, 0 & 0xFF),
            call(address, base_addr + 1, 0 >> 8),
            call(address, base_addr + 2, expected_off & 0xFF),
            call(address, base_addr + 3, expected_off >> 8),
        ]
        mock_bus.write_byte_data.assert_has_calls(expected_calls, any_order=False)
        mock_bus.write_byte_data.reset_mock()

        duty = 50
        expected_pulse = int((duty / 100.0) * pwm._period)  # type: ignore
        pwm.set_pwm_duty_cycle(channel, duty)
        expected_calls = [
            call(address, base_addr, 0 & 0xFF),
            call(address, base_addr + 1, 0 >> 8),
            call(address, base_addr + 2, expected_pulse & 0xFF),
            call(address, base_addr + 3, expected_pulse >> 8),
        ]
        mock_bus.write_byte_data.assert_has_calls(expected_calls, any_order=False)
        mock_bus.write_byte_data.reset_mock()

        with self.assertRaises(ValueError):
            pwm.set_pwm_duty_cycle(channel, -1)
        with self.assertRaises(ValueError):
            pwm.set_pwm_duty_cycle(channel, 101)


if __name__ == "__main__":
    unittest.main()
