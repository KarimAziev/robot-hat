import unittest
from unittest.mock import MagicMock

from robot_hat import MotorServiceDirection, MotorZeroDirection, SingleMotorService
from robot_hat.data_types.motor import (
    MotorServiceDirection as DataMotorServiceDirection,
)
from robot_hat.data_types.motor import MotorZeroDirection as DataMotorZeroDirection


class TestSingleMotorService(unittest.TestCase):
    def setUp(self):
        self.motor = MagicMock()
        self.controller = SingleMotorService(self.motor)

    def test_public_direction_types_are_exported_from_shared_data_types(self):
        self.assertIs(MotorServiceDirection, DataMotorServiceDirection)
        self.assertIs(MotorZeroDirection, DataMotorZeroDirection)

    def test_move_forward_sets_positive_speed(self):
        self.controller.move(60, 1)

        self.motor.set_speed.assert_called_once_with(60)
        self.assertEqual(self.controller.direction, 1)

    def test_move_backward_sets_negative_speed(self):
        self.controller.move(60, -1)

        self.motor.set_speed.assert_called_once_with(-60)
        self.assertEqual(self.controller.direction, -1)

    def test_move_with_zero_direction_stops_motor_twice(self):
        self.controller.move(60, 0)

        self.motor.set_speed.assert_not_called()
        self.assertEqual(self.motor.stop.call_count, 2)
        self.assertEqual(self.controller.direction, 0)

    def test_stop_all_stops_motor_twice(self):
        self.controller.stop_all()

        self.assertEqual(self.motor.stop.call_count, 2)
        self.assertEqual(self.controller.direction, 0)

    def test_speed_returns_absolute_motor_speed(self):
        self.motor.speed = -42.5

        self.assertEqual(self.controller.speed, 42.5)

    def test_update_calibration_speed(self):
        self.motor.update_calibration_speed.return_value = 10

        result = self.controller.update_calibration_speed(5, persist=True)

        self.motor.update_calibration_speed.assert_called_once_with(5, True)
        self.assertEqual(result, 10)

    def test_update_calibration_direction(self):
        self.motor.update_calibration_direction.return_value = -1

        result = self.controller.update_calibration_direction(-1, persist=True)

        self.motor.update_calibration_direction.assert_called_once_with(-1, True)
        self.assertEqual(result, -1)

    def test_reset_calibration_resets_motor_direction_and_speed(self):
        self.controller.reset_calibration()

        self.motor.reset_calibration_direction.assert_called_once()
        self.motor.reset_calibration_speed.assert_called_once()

    def test_close_closes_motor_and_clears_reference(self):
        self.controller.close()

        self.motor.close.assert_called_once()
        self.assertIsNone(self.controller.motor)


if __name__ == "__main__":
    unittest.main()
