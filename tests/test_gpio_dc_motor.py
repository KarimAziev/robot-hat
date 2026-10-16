import unittest
from unittest.mock import MagicMock, call, patch

from gpiozero import Device, OutputDevice
from gpiozero.pins.mock import MockFactory, MockPWMPin

from robot_hat import GPIODCMotor


class TestGPIOMotor(unittest.TestCase):
    def setUp(self):
        patcher = patch("gpiozero.Motor")
        self.addCleanup(patcher.stop)
        self.MockMotor = patcher.start()
        enable_patcher = patch("gpiozero.DigitalOutputDevice")
        self.addCleanup(enable_patcher.stop)
        self.enable_class = enable_patcher.start()
        self.enable = self.enable_class.return_value

        self.motor_mock = MagicMock()
        self.motor_mock.forward = MagicMock()
        self.motor_mock.backward = MagicMock()
        self.motor_mock.stop = MagicMock()
        self.motor_mock.close = MagicMock()
        self.motor_mock.forward_device = MagicMock(spec=OutputDevice)
        self.motor_mock.backward_device = MagicMock(spec=OutputDevice)

        self.MockMotor.return_value = self.motor_mock

    def test_init_default_name_and_motor_created(self):
        m = GPIODCMotor(forward_pin=5, backward_pin=6, pwm_pin=12, pwm=True)
        self.MockMotor.assert_called_once_with(forward=5, backward=6, pwm=True)
        self.enable_class.assert_called_once_with(12, initial_value=False)
        expected_name = "F5-B6-P12"
        self.assertEqual(m.name, expected_name)

    def test_set_speed_forward_with_pwm_calls_forward_with_scaled_value_and_sets_speed(
        self,
    ):
        m = GPIODCMotor(
            forward_pin=2, backward_pin=3, pwm_pin=4, pwm=True, max_speed=100
        )
        m.set_speed(50)
        self.motor_mock.forward.assert_called_once_with(0.5)
        self.assertEqual(m.speed, 50)

    def test_set_speed_backward_with_pwm_calls_backward_and_sets_speed(self):
        m = GPIODCMotor(
            forward_pin=2, backward_pin=3, pwm_pin=4, pwm=True, max_speed=100
        )
        m.set_speed(-30)
        self.motor_mock.backward.assert_called_once_with(0.3)
        self.assertEqual(m.speed, -30)

    def test_set_speed_with_calibration_direction_negative_swaps_commands(self):
        m = GPIODCMotor(
            forward_pin=7,
            backward_pin=8,
            pwm_pin=9,
            pwm=True,
            calibration_direction=-1,
            max_speed=100,
        )
        m.set_speed(40)
        self.motor_mock.backward.assert_called_once_with(0.4)
        self.assertEqual(m.speed, 40)
        self.assertEqual(m.applied_speed, -40)

    def test_set_speed_applies_offset_to_magnitude(self):
        m = GPIODCMotor(
            forward_pin=7,
            backward_pin=8,
            pwm_pin=9,
            pwm=True,
            calibration_speed_offset=10,
            max_speed=100,
        )

        m.set_speed(-40)

        self.motor_mock.backward.assert_called_once_with(0.5)
        self.assertEqual(m.speed, -40)
        self.assertEqual(m.applied_speed, -50)

    def test_set_speed_zero_with_offset_stops(self):
        m = GPIODCMotor(
            forward_pin=7,
            backward_pin=8,
            pwm_pin=9,
            pwm=True,
            calibration_speed_offset=10,
        )

        m.set_speed(0)

        self.motor_mock.stop.assert_called_once()
        self.motor_mock.forward.assert_not_called()
        self.motor_mock.backward.assert_not_called()

    def test_set_speed_without_pwm_preserves_logical_and_reports_full_output(self):
        m = GPIODCMotor(
            forward_pin=1, backward_pin=0, pwm_pin=None, pwm=False, max_speed=80
        )
        m.set_speed(30)
        self.motor_mock.forward.assert_called_once_with(1)
        self.assertEqual(m.speed, 30)
        self.assertEqual(m.applied_speed, 80)

        self.motor_mock.reset_mock()
        m.set_speed(-10)
        self.motor_mock.backward.assert_called_once_with(1)
        self.assertEqual(m.speed, -10)
        self.assertEqual(m.applied_speed, -80)

    def test_stop_calls_motor_stop_and_sets_speed_zero(self):
        m = GPIODCMotor(forward_pin=11, backward_pin=12, pwm_pin=13, pwm=True)
        m.set_speed(20)
        self.motor_mock.reset_mock()
        m.stop()
        self.motor_mock.stop.assert_called_once()
        self.assertEqual(m.speed, 0)
        self.assertEqual(m.applied_speed, 0)

    def test_close_calls_motor_close_if_present(self):
        m = GPIODCMotor(forward_pin=21, backward_pin=22, pwm_pin=23, pwm=True)
        m.close()
        self.motor_mock.close.assert_called_once()

    def test_apply_speed_correction_clamps_to_max_speed(self):
        m = GPIODCMotor(
            forward_pin=4, backward_pin=5, pwm_pin=6, pwm=True, max_speed=60
        )
        m.set_speed(100)
        self.motor_mock.forward.assert_called_once_with(1.0)
        self.assertEqual(m.speed, 60)

        self.motor_mock.reset_mock()
        m.set_speed(-200)
        self.motor_mock.backward.assert_called_once_with(1.0)
        self.assertEqual(m.speed, -60)

    def test_set_speed_zero_calls_stop(self):
        m = GPIODCMotor(forward_pin=3, backward_pin=4, pwm_pin=5, pwm=True)
        m.set_speed(0)
        self.motor_mock.stop.assert_called_once()
        self.assertEqual(m.speed, 0)

    def test_del_calls_close(self):
        m = GPIODCMotor(forward_pin=9, backward_pin=10, pwm_pin=11, pwm=True)
        m.__del__()
        self.motor_mock.close.assert_called_once()

    def test_enable_is_low_until_direction_is_ready(self):
        events = MagicMock()
        events.attach_mock(self.enable, "enable")
        events.attach_mock(self.motor_mock, "motor")
        m = GPIODCMotor(20, 21, 26)
        events.reset_mock()

        m.set_speed(40)

        self.assertEqual(
            events.mock_calls,
            [call.enable.off(), call.motor.forward(0.4), call.enable.on()],
        )

    def test_close_disables_before_stopping_and_releases_enable_last(self):
        events = MagicMock()
        events.attach_mock(self.enable, "enable")
        events.attach_mock(self.motor_mock, "motor")
        m = GPIODCMotor(20, 21, 26)
        events.reset_mock()

        m.close()
        m.close()

        self.assertEqual(
            events.mock_calls,
            [
                call.enable.off(),
                call.motor.stop(),
                call.motor.close(),
                call.enable.close(),
            ],
        )
        with self.assertRaisesRegex(RuntimeError, "closed"):
            m.set_speed(50)

    def test_stop_still_clears_direction_if_disabling_fails(self):
        m = GPIODCMotor(20, 21, 26)
        self.enable.off.side_effect = OSError("enable failure")

        with self.assertRaisesRegex(OSError, "enable failure"):
            m.stop()

        self.motor_mock.stop.assert_called_once()
        self.enable.off.side_effect = None

    def test_stop_failure_attempts_both_direction_outputs(self):
        m = GPIODCMotor(20, 21, 26)
        self.motor_mock.stop.side_effect = OSError("direction failure")

        with self.assertRaisesRegex(OSError, "direction failure"):
            m.stop()

        self.motor_mock.forward_device.off.assert_called_once()
        self.motor_mock.backward_device.off.assert_called_once()
        self.motor_mock.stop.side_effect = None

    def test_failed_command_disables_and_stops(self):
        m = GPIODCMotor(20, 21, 26)
        self.motor_mock.forward.side_effect = OSError("command failed")

        with self.assertRaisesRegex(OSError, "command failed"):
            m.set_speed(60)

        self.enable.on.assert_not_called()
        self.motor_mock.stop.assert_called_once()

    def test_constructor_failure_releases_disabled_enable(self):
        self.MockMotor.side_effect = OSError("direction unavailable")

        with self.assertRaisesRegex(OSError, "direction unavailable"):
            GPIODCMotor(20, 21, 26)

        self.enable.on.assert_not_called()
        self.enable.close.assert_called_once()


class TestGPIOMotorPins(unittest.TestCase):
    def test_enable_stays_low_outside_motion_with_real_gpiozero_devices(self) -> None:
        factory = MockFactory(pin_class=MockPWMPin)
        with patch.object(Device, "pin_factory", factory):
            motor = GPIODCMotor("GPIO20", "GPIO21", "GPIO26")
            try:
                enable = factory.pin(26)
                forward = factory.pin(20)
                backward = factory.pin(21)
                self.assertFalse(enable.state)
                self.assertTrue(all(state.state == 0 for state in enable.states))

                motor.set_speed(40)
                self.assertTrue(enable.state)
                self.assertEqual(forward.state, 0.4)
                self.assertFalse(backward.state)

                motor.stop()
                self.assertFalse(enable.state)
                self.assertFalse(forward.state)
                self.assertFalse(backward.state)

                motor.set_speed(-60)
                motor.close()
                self.assertFalse(enable.state)
                self.assertFalse(forward.state)
                self.assertFalse(backward.state)
            finally:
                motor.close()
                factory.close()


if __name__ == "__main__":
    unittest.main()
