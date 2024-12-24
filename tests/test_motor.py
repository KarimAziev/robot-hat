import unittest
from unittest.mock import MagicMock

from robot_hat import PWM, Pin
from robot_hat.motor.motor import Motor


class TestMotor(unittest.TestCase):
    def setUp(self):
        self.mock_dir_pin = MagicMock(spec=Pin)
        self.mock_pwm_pin = MagicMock(spec=PWM)
        self.motor = Motor(
            dir_pin=self.mock_dir_pin,
            pwm_pin=self.mock_pwm_pin,
            calibration_direction=1,
            calibration_speed_offset=0,
            max_speed=100,
            period=4095,
            prescaler=10,
            name="TestMotor",
        )

    def test_motor_initialization(self):
        self.assertEqual(self.motor.calibration_direction, 1)
        self.assertEqual(self.motor.calibration_speed_offset, 0)
        self.assertEqual(self.motor.max_speed, 100)
        self.assertEqual(self.motor.direction, 1)
        self.assertEqual(self.motor.speed_offset, 0)
        self.assertEqual(self.motor.period, 4095)
        self.assertEqual(self.motor.prescaler, 10)
        self.assertEqual(self.motor.name, "TestMotor")
        self.mock_pwm_pin.period.assert_called_once_with(4095)
        self.mock_pwm_pin.prescaler.assert_called_once_with(10)

    def test_set_speed_forward(self):
        self.motor.set_speed(50)
        self.mock_dir_pin.low.assert_called_once()
        self.mock_pwm_pin.pulse_width_percent.assert_called_once_with(75)
        self.assertEqual(self.motor.speed, 50)

    def test_set_speed_reverse(self):
        self.motor.set_speed(-50)
        self.mock_dir_pin.high.assert_called_once()
        self.mock_pwm_pin.pulse_width_percent.assert_called_once_with(75)
        self.assertEqual(self.motor.speed, -50)

    def test_set_speed_with_calibration(self):
        self.motor.update_calibration_speed(10, persist=True)
        self.motor.set_speed(50)
        self.mock_pwm_pin.pulse_width_percent.assert_called_once_with(65)
        self.assertEqual(self.motor.speed, 50)

    def test_set_speed_constraints(self):
        self.motor.set_speed(120)
        self.mock_pwm_pin.pulse_width_percent.assert_called_once_with(100)
        self.assertEqual(self.motor.speed, 100)
        self.motor.set_speed(-120)
        self.mock_pwm_pin.pulse_width_percent.assert_called_with(100)
        self.assertEqual(self.motor.speed, -100)

    def test_update_calibration_speed(self):
        initial_speed_offset = self.motor.calibration_speed_offset
        offset = self.motor.update_calibration_speed(15)
        self.assertEqual(offset, 15)
        self.assertEqual(self.motor.speed_offset, 15)
        self.assertEqual(self.motor.calibration_speed_offset, initial_speed_offset)

    def test_reset_calibration_speed(self):
        initial_speed_offset = self.motor.calibration_speed_offset
        self.motor.update_calibration_speed(20, persist=False)
        self.assertEqual(self.motor.speed_offset, 20)
        self.assertEqual(self.motor.calibration_speed_offset, initial_speed_offset)
        self.motor.reset_calibration_speed()
        self.assertEqual(self.motor.speed_offset, initial_speed_offset)
        self.assertEqual(self.motor.calibration_speed_offset, initial_speed_offset)

    def test_reset_calibration_speed_persisted(self):
        self.motor.update_calibration_speed(20, persist=True)
        self.assertEqual(self.motor.speed_offset, 20)
        self.assertEqual(self.motor.calibration_speed_offset, 20)
        self.motor.reset_calibration_speed()
        self.assertEqual(self.motor.speed_offset, 20)
        self.assertEqual(self.motor.calibration_speed_offset, 20)

    def test_update_calibration_direction(self):
        new_direction = self.motor.update_calibration_direction(-1, persist=True)
        self.assertEqual(new_direction, -1)
        self.assertEqual(self.motor.direction, -1)

    def test_reset_calibration_direction(self):
        initial_direction = self.motor.direction
        self.motor.update_calibration_direction(-1, persist=False)
        self.motor.reset_calibration_direction()
        self.assertEqual(self.motor.direction, initial_direction)

        self.motor.update_calibration_direction(-1, persist=True)
        self.motor.reset_calibration_direction()
        self.assertEqual(self.motor.direction, -1)

    def test_reset_calibration(self):
        initial_dir_calibration = self.motor.calibration_direction
        initial_speed_calibration = self.motor.calibration_speed_offset
        self.motor.update_calibration_speed(15)
        self.motor.update_calibration_direction(-1)
        self.motor.reset_calibration()
        self.assertEqual(self.motor.direction, initial_dir_calibration)
        self.assertEqual(self.motor.speed_offset, initial_speed_calibration)

    def test_reset_calibration_persisted(self):
        self.motor.update_calibration_speed(15, persist=True)
        self.motor.update_calibration_direction(-1, persist=True)
        self.motor.reset_calibration()
        self.assertEqual(self.motor.speed_offset, 15)
        self.assertEqual(self.motor.direction, -1)

    def test_stop(self):
        self.motor.stop()
        self.mock_pwm_pin.pulse_width_percent.assert_called_once_with(0)
        self.assertEqual(self.motor.speed, 0)

    def test_pwm_conversion(self):
        pwm_value = self.motor._convert_speed_to_pwm(50)
        self.assertEqual(pwm_value, 75)
        self.assertEqual(self.motor._convert_speed_to_pwm(-50), 75)

    def test_constraints_on_pwm(self):
        constrained_pwm = self.motor._apply_pwm_constraints(150)
        self.assertEqual(constrained_pwm, 100)

    def test_speed_to_pwm_formula(self):
        self.assertEqual(self.motor.speed_to_pwm_formula(100), 100)
        self.assertEqual(self.motor.speed_to_pwm_formula(-100), 100)
        self.assertEqual(self.motor.speed_to_pwm_formula(10), 55)
        self.assertEqual(self.motor.speed_to_pwm_formula(-10), 55)
        self.assertEqual(self.motor.speed_to_pwm_formula(-40), 70)
        self.assertEqual(self.motor.speed_to_pwm_formula(40), 70)
        self.assertEqual(self.motor.speed_to_pwm_formula(50), 75)
        self.assertEqual(self.motor.speed_to_pwm_formula(55), 77)

    def test_repr(self):
        representation = repr(self.motor)
        self.assertIn("TestMotor", representation)


if __name__ == "__main__":
    unittest.main()
