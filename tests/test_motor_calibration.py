import unittest

from robot_hat import MotorCalibrationMixin, MotorValidationError


class TestMotorCalibrationMixin(unittest.TestCase):
    def setUp(self):
        self.mc = MotorCalibrationMixin()

    def test_initial_values_default(self):
        self.assertEqual(self.mc.calibration_direction, 1)
        self.assertEqual(self.mc.direction, 1)
        self.assertEqual(self.mc.calibration_speed_offset, 0)
        self.assertEqual(self.mc.speed_offset, 0)

    def test_initial_values_custom(self):
        mc2 = MotorCalibrationMixin(
            calibration_direction=-1, calibration_speed_offset=0.5
        )
        self.assertEqual(mc2.calibration_direction, -1)
        self.assertEqual(mc2.direction, -1)
        self.assertEqual(mc2.calibration_speed_offset, 0.5)
        self.assertEqual(mc2.speed_offset, 0.5)

    def test_init_with_invalid_direction_raises(self):
        with self.assertRaises(MotorValidationError):
            MotorCalibrationMixin(calibration_direction=0)  # type: ignore

    def test_direction_setter_validation(self):
        with self.assertRaises(MotorValidationError):
            self.mc.direction = 0  # type: ignore
        with self.assertRaises(MotorValidationError):
            self.mc.direction = 2  # type: ignore
        with self.assertRaises(MotorValidationError):
            self.mc.direction = None  # type: ignore

    def test_calibration_direction_setter_validation(self):
        with self.assertRaises(MotorValidationError):
            self.mc.calibration_direction = 0  # type: ignore
        with self.assertRaises(MotorValidationError):
            self.mc.calibration_direction = 2  # type: ignore

    def test_update_calibration_speed_temporary(self):
        original_persisted = self.mc.calibration_speed_offset
        returned = self.mc.update_calibration_speed(0.25, persist=False)
        self.assertEqual(returned, 0.25)
        self.assertEqual(self.mc.speed_offset, 0.25)
        self.assertEqual(self.mc.calibration_speed_offset, original_persisted)

    def test_update_calibration_speed_persistent(self):
        returned = self.mc.update_calibration_speed(1.5, persist=True)
        self.assertEqual(returned, 1.5)
        self.assertEqual(self.mc.speed_offset, 1.5)
        self.assertEqual(self.mc.calibration_speed_offset, 1.5)

    def test_reset_calibration_speed(self):
        self.mc.update_calibration_speed(2.3, persist=True)
        self.mc.speed_offset = 5.0
        reset_val = self.mc.reset_calibration_speed()
        self.assertEqual(reset_val, self.mc.calibration_speed_offset)
        self.assertEqual(self.mc.speed_offset, self.mc.calibration_speed_offset)
        self.assertEqual(self.mc.speed_offset, 2.3)

    def test_update_calibration_direction_temporary(self):
        original_persisted = self.mc.calibration_direction
        returned = self.mc.update_calibration_direction(-1, persist=False)
        self.assertEqual(returned, -1)
        self.assertEqual(self.mc.direction, -1)
        self.assertEqual(self.mc.calibration_direction, original_persisted)

    def test_update_calibration_direction_persistent(self):
        returned = self.mc.update_calibration_direction(-1, persist=True)
        self.assertEqual(returned, -1)
        self.assertEqual(self.mc.direction, -1)
        self.assertEqual(self.mc.calibration_direction, -1)

    def test_reset_calibration_direction(self):
        self.mc.update_calibration_direction(-1, persist=True)
        self.mc.direction = 1
        reset_val = self.mc.reset_calibration_direction()
        self.assertEqual(reset_val, self.mc.calibration_direction)
        self.assertEqual(self.mc.direction, self.mc.calibration_direction)
        self.assertEqual(self.mc.direction, -1)

    def test_reset_calibration_calls_both(self):
        self.mc.update_calibration_direction(-1, persist=True)
        self.mc.update_calibration_speed(0.7, persist=True)

        self.mc.direction = 1
        self.mc.speed_offset = 3.14

        self.mc.reset_calibration()
        self.assertEqual(self.mc.direction, -1)
        self.assertEqual(self.mc.speed_offset, 0.7)

    def test_update_calibration_direction_returns_current(self):
        ret = self.mc.update_calibration_direction(-1, persist=False)
        self.assertEqual(ret, self.mc.direction)
        self.assertEqual(ret, -1)

    def test_update_calibration_speed_returns_current(self):
        ret = self.mc.update_calibration_speed(9.99, persist=False)
        self.assertEqual(ret, self.mc.speed_offset)
        self.assertEqual(ret, 9.99)


if __name__ == "__main__":
    unittest.main()
