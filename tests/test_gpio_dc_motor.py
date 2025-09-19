import unittest
from unittest.mock import MagicMock, patch

from robot_hat import GPIODCMotor


class TestGPIOMotor(unittest.TestCase):
    def setUp(self):
        patcher = patch("gpiozero.Motor")
        self.addCleanup(patcher.stop)
        self.MockMotor = patcher.start()

        self.motor_mock = MagicMock()
        self.motor_mock.forward = MagicMock()
        self.motor_mock.backward = MagicMock()
        self.motor_mock.stop = MagicMock()
        self.motor_mock.close = MagicMock()

        self.MockMotor.return_value = self.motor_mock

    def test_init_default_name_and_motor_created(self):
        m = GPIODCMotor(forward_pin=5, backward_pin=6, pwm_pin=12, pwm=True)
        self.MockMotor.assert_called_once_with(
            forward=5, backward=6, enable=12, pwm=True
        )
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

    def test_set_speed_without_pwm_uses_full_on_and_sets_speed_to_max(self):
        m = GPIODCMotor(
            forward_pin=1, backward_pin=0, pwm_pin=None, pwm=False, max_speed=80
        )
        m.set_speed(30)
        self.motor_mock.forward.assert_called_once_with(1)
        self.assertEqual(m.speed, 80)

        self.motor_mock.reset_mock()
        m.set_speed(-10)
        self.motor_mock.backward.assert_called_once_with(1)
        self.assertEqual(m.speed, -80)

    def test_stop_calls_motor_stop_and_sets_speed_zero(self):
        m = GPIODCMotor(forward_pin=11, backward_pin=12, pwm_pin=13, pwm=True)
        m.set_speed(20)
        self.motor_mock.reset_mock()
        m.stop()
        self.motor_mock.stop.assert_called_once()
        self.assertEqual(m.speed, 0)

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


if __name__ == "__main__":
    unittest.main()
