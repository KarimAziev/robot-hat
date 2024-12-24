import unittest
from unittest.mock import MagicMock

from robot_hat.services.motor_service import MotorService


class TestMotorController(unittest.TestCase):
    def setUp(self):
        self.left_motor = MagicMock()
        self.right_motor = MagicMock()

        self.controller = MotorService(self.left_motor, self.right_motor)

    def test_stop_all(self):

        self.controller.stop_all()

        self.assertEqual(self.left_motor.stop.call_count, 2)
        self.assertEqual(self.right_motor.stop.call_count, 2)

    def test_update_left_motor_calibration_speed(self):
        self.left_motor.update_calibration_speed.return_value = 10

        result = self.controller.update_left_motor_calibration_speed(5, persist=True)

        self.left_motor.update_calibration_speed.assert_called_once_with(5, True)

        self.assertEqual(result, 10)

    def test_update_right_motor_calibration_speed(self):
        self.right_motor.update_calibration_speed.return_value = -3

        result = self.controller.update_right_motor_calibration_speed(-5, persist=False)

        self.right_motor.update_calibration_speed.assert_called_once_with(-5, False)

        self.assertEqual(result, -3)

    def test_update_left_motor_calibration_direction(self):

        self.left_motor.update_calibration_direction.return_value = 1

        result = self.controller.update_left_motor_calibration_direction(
            1, persist=False
        )

        self.left_motor.update_calibration_direction.assert_called_once_with(1, False)

        self.assertEqual(result, 1)

    def test_update_right_motor_calibration_direction(self):

        self.right_motor.update_calibration_direction.return_value = -1
        result = self.controller.update_right_motor_calibration_direction(
            -1, persist=True
        )

        self.right_motor.update_calibration_direction.assert_called_once_with(-1, True)

        self.assertEqual(result, -1)

    def test_speed_property(self):
        # Test when both motors have positive speeds
        self.left_motor.speed = 50
        self.right_motor.speed = 70
        self.assertEqual(self.controller.speed, 60)  # (|50| + |70|) / 2 = 60

        # Test when motors have negative speeds
        self.left_motor.speed = -40
        self.right_motor.speed = -60
        self.assertEqual(self.controller.speed, 50)  # (|40| + |60|) / 2 = 50

        # Test when one motor is stopped (speed = 0)
        self.left_motor.speed = 0
        self.right_motor.speed = 80
        self.assertEqual(self.controller.speed, 40)  # (|0| + |80|) / 2 = 40

        # Test when both motors are stopped (speed = 0)
        self.left_motor.speed = 0
        self.right_motor.speed = 0
        self.assertEqual(self.controller.speed, 0)  # (|0| + |0|) / 2 = 0

        # Test with floating-point speeds
        self.left_motor.speed = 33.33
        self.right_motor.speed = 66.66
        self.assertAlmostEqual(self.controller.speed, 50.0, places=2)  # Approximation

        # Test with mixed positive and negative speeds
        self.left_motor.speed = -45
        self.right_motor.speed = 55
        self.assertEqual(self.controller.speed, 50)  # (|45| + |55|) / 2 = 50

        self.left_motor.speed = -100
        self.right_motor.speed = 100
        self.assertEqual(self.controller.speed, 100)

        self.left_motor.speed = -50
        self.right_motor.speed = 50
        self.assertEqual(self.controller.speed, 50)

    def test_reset_calibration(self):

        self.controller.reset_calibration()

        self.left_motor.reset_calibration_direction.assert_called_once()
        self.left_motor.reset_calibration_speed.assert_called_once()
        self.right_motor.reset_calibration_direction.assert_called_once()
        self.right_motor.reset_calibration_speed.assert_called_once()

    def test_move_forward(self):
        self.controller.move_with_steering(speed=60, direction=1)
        self.left_motor.set_speed.assert_called_once_with(60)
        self.right_motor.set_speed.assert_called_once_with(-60)

    def test_move_backward(self):
        self.controller.move_with_steering(speed=60, direction=-1)
        self.left_motor.set_speed.assert_called_once_with(-60)
        self.right_motor.set_speed.assert_called_once_with(60)

    def test_move_with_steering_forward(self):
        self.controller.move_with_steering(speed=80, direction=1, current_angle=0)

        self.left_motor.set_speed.assert_called_once_with(80)
        self.right_motor.set_speed.assert_called_once_with(-80)

    def test_move_with_steering_backward(self):
        self.controller.move_with_steering(speed=60, direction=-1, current_angle=0)

        self.left_motor.set_speed.assert_called_once_with(-60)
        self.right_motor.set_speed.assert_called_once_with(60)

    def test_move_with_steering(self):
        self.controller.move_with_steering(speed=10, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(10)
        self.right_motor.set_speed.assert_called_with(-7.0)
        self.controller.move_with_steering(speed=20, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(20)
        self.right_motor.set_speed.assert_called_with(-14.0)
        self.controller.move_with_steering(speed=30, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(30)
        self.right_motor.set_speed.assert_called_with(-21.0)
        self.controller.move_with_steering(speed=40, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(40)
        self.right_motor.set_speed.assert_called_with(-28.0)
        self.controller.move_with_steering(speed=50, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(50)
        self.right_motor.set_speed.assert_called_with(-35.0)
        self.controller.move_with_steering(speed=60, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(60)
        self.right_motor.set_speed.assert_called_with(-42.0)
        self.controller.move_with_steering(speed=70, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(70)
        self.right_motor.set_speed.assert_called_with(-49.0)
        self.controller.move_with_steering(speed=80, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(80)
        self.right_motor.set_speed.assert_called_with(-56.0)
        self.controller.move_with_steering(speed=90, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(90)
        self.right_motor.set_speed.assert_called_with(-62.99999999999999)
        self.controller.move_with_steering(speed=100, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(100)
        self.right_motor.set_speed.assert_called_with(-70.0)
        self.controller.move_with_steering(speed=10, direction=-1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(-10)
        self.right_motor.set_speed.assert_called_with(7.0)
        self.controller.move_with_steering(speed=20, direction=-1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(-20)
        self.right_motor.set_speed.assert_called_with(14.0)
        self.controller.move_with_steering(speed=30, direction=-1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(-30)
        self.right_motor.set_speed.assert_called_with(21.0)
        self.controller.move_with_steering(speed=10, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(10)
        self.right_motor.set_speed.assert_called_with(-7.0)
        self.controller.move_with_steering(speed=20, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(20)
        self.right_motor.set_speed.assert_called_with(-14.0)
        self.controller.move_with_steering(speed=30, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(30)
        self.right_motor.set_speed.assert_called_with(-21.0)
        self.controller.move_with_steering(speed=40, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(40)
        self.right_motor.set_speed.assert_called_with(-28.0)
        self.controller.move_with_steering(speed=50, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(50)
        self.right_motor.set_speed.assert_called_with(-35.0)
        self.controller.move_with_steering(speed=60, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(60)
        self.right_motor.set_speed.assert_called_with(-42.0)
        self.controller.move_with_steering(speed=70, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(70)
        self.right_motor.set_speed.assert_called_with(-49.0)
        self.controller.move_with_steering(speed=80, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(80)
        self.right_motor.set_speed.assert_called_with(-56.0)
        self.controller.move_with_steering(speed=90, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(90)
        self.right_motor.set_speed.assert_called_with(-62.99999999999999)
        self.controller.move_with_steering(speed=100, direction=1, current_angle=-30)
        self.left_motor.set_speed.assert_called_with(100)
        self.right_motor.set_speed.assert_called_with(-70.0)
        self.controller.move_with_steering(speed=10, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(7.0)
        self.right_motor.set_speed.assert_called_with(-10)
        self.controller.move_with_steering(speed=20, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(14.0)
        self.right_motor.set_speed.assert_called_with(-20)
        self.controller.move_with_steering(speed=30, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(21.0)
        self.right_motor.set_speed.assert_called_with(-30)
        self.controller.move_with_steering(speed=40, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(28.0)
        self.right_motor.set_speed.assert_called_with(-40)
        self.controller.move_with_steering(speed=50, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(35.0)
        self.right_motor.set_speed.assert_called_with(-50)
        self.controller.move_with_steering(speed=60, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(42.0)
        self.right_motor.set_speed.assert_called_with(-60)
        self.controller.move_with_steering(speed=70, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(49.0)
        self.right_motor.set_speed.assert_called_with(-70)
        self.controller.move_with_steering(speed=80, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(56.0)
        self.right_motor.set_speed.assert_called_with(-80)
        self.controller.move_with_steering(speed=90, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(62.99999999999999)
        self.right_motor.set_speed.assert_called_with(-90)
        self.controller.move_with_steering(speed=100, direction=1, current_angle=30)
        self.left_motor.set_speed.assert_called_with(70.0)
        self.right_motor.set_speed.assert_called_with(-100)


if __name__ == "__main__":
    unittest.main()
