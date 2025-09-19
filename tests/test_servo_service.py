import unittest
from unittest.mock import Mock

from robot_hat import (
    InvalidCalibrationModeError,
    ServoABC,
    ServoCalibrationMode,
    ServoService,
)


class FakeServo(ServoABC):
    """
    Fake servo implementing ServoABC.
    """

    def __init__(self):
        self.angle_calls = Mock()
        self.reset_calls = Mock()
        self.close_calls = Mock()

    def angle(self, angle: float) -> None:
        self.angle_calls(angle)

    def reset(self) -> None:
        self.reset_calls()

    def close(self) -> None:
        self.close_calls()


class TestServoService(unittest.TestCase):
    def setUp(self):
        self.fake_servo = FakeServo()

    def test_initialization_calls_servo_with_initial_calibration_offset(self):
        s = ServoService(
            servo=self.fake_servo, name="test", min_angle=-90, max_angle=90
        )
        self.fake_servo.angle_calls.assert_called_with(0.0)
        self.assertEqual(s.name, "test")
        self.assertEqual(s.min_angle, -90)
        self.assertEqual(s.max_angle, 90)
        self.assertEqual(s.current_angle, 0.0)

    def test_apply_sum_and_negative_calibration(self):
        self.assertEqual(ServoService.apply_sum_calibration(10.0, 2.5), 12.5)
        self.assertEqual(ServoService.apply_negative_calibration(10.0, 2.0), -8.0)

    def test_set_angle_with_sum_calibration(self):
        s = ServoService(
            servo=self.fake_servo,
            name="sum",
            min_angle=-45,
            max_angle=45,
            calibration_offset=1.5,
            calibration_mode=ServoCalibrationMode.SUM,
        )

        s.set_angle(10)
        self.fake_servo.angle_calls.assert_called_with(11.5)
        self.assertEqual(s.current_angle, 10)

        s.set_angle(100)
        self.fake_servo.angle_calls.assert_called_with(46.5)
        self.assertEqual(s.current_angle, 45)

        s.set_angle(-100)
        self.fake_servo.angle_calls.assert_called_with(-43.5)
        self.assertEqual(s.current_angle, -45)

    def test_set_angle_with_negative_calibration(self):
        s = ServoService(
            servo=self.fake_servo,
            name="neg",
            min_angle=-30,
            max_angle=30,
            calibration_offset=2.0,
            calibration_mode=ServoCalibrationMode.NEGATIVE,
        )

        s.set_angle(10)
        self.fake_servo.angle_calls.assert_called_with(-8.0)
        self.assertEqual(s.current_angle, 10)

    def test_set_angle_with_custom_calibration_function(self):
        custom = lambda value, calib: value * 2 + calib
        s = ServoService(
            servo=self.fake_servo,
            name="custom",
            min_angle=-100,
            max_angle=100,
            calibration_offset=3.0,
            calibration_mode=custom,
        )

        s.set_angle(7)
        self.fake_servo.angle_calls.assert_called_with(17.0)
        self.assertEqual(s.current_angle, 7)

    def test_set_angle_with_calibration_disabled(self):
        s = ServoService(
            servo=self.fake_servo,
            name="none_calib",
            min_angle=-20,
            max_angle=20,
            calibration_offset=5.0,
            calibration_mode=None,
        )

        s.set_angle(15)
        self.fake_servo.angle_calls.assert_called_with(15)
        self.assertEqual(s.current_angle, 15)

        s.set_angle(30)
        self.fake_servo.angle_calls.assert_called_with(20)
        self.assertEqual(s.current_angle, 20)

    def test_reverse_option_inverts_input_before_constraints(self):
        s = ServoService(
            servo=self.fake_servo,
            name="rev",
            min_angle=-40,
            max_angle=40,
            calibration_offset=1.0,
            calibration_mode=ServoCalibrationMode.SUM,
            reverse=True,
        )

        s.set_angle(30)
        self.fake_servo.angle_calls.assert_called_with(-29.0)
        self.assertEqual(s.current_angle, -30)

        s.set_angle(-100)
        self.fake_servo.angle_calls.assert_called_with(41.0)
        self.assertEqual(s.current_angle, 40)

    def test_update_calibration_non_persistent_and_persistent(self):
        s = ServoService(
            servo=self.fake_servo,
            name="update",
            min_angle=-90,
            max_angle=90,
            calibration_offset=0.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )

        new = s.update_calibration(2.25, persist=False)
        self.assertEqual(new, 2.25)
        self.assertEqual(s.calibration_offset, 2.25)
        self.fake_servo.angle_calls.assert_called_with(2.25)
        self.assertEqual(s._persisted_calibration_offset, 0.0)

        new2 = s.update_calibration(-1.5, persist=True)
        self.assertEqual(new2, -1.5)
        self.assertEqual(s.calibration_offset, -1.5)
        self.assertEqual(s._persisted_calibration_offset, -1.5)
        self.fake_servo.angle_calls.assert_called_with(-1.5)

    def test_reset_calibration_restores_persisted(self):
        s = ServoService(
            servo=self.fake_servo,
            name="reset",
            min_angle=-90,
            max_angle=90,
            calibration_offset=5.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )

        s.update_calibration(2.0, persist=True)
        self.assertEqual(s.calibration_offset, 2.0)
        s.update_calibration(4.0, persist=False)
        self.assertEqual(s.calibration_offset, 4.0)
        restored = s.reset_calibration()
        self.assertEqual(restored, 2.0)
        self.fake_servo.angle_calls.assert_called_with(2.0)

    def test_reset_calls_set_angle_zero(self):
        s = ServoService(
            servo=self.fake_servo,
            name="reset_zero",
            min_angle=-90,
            max_angle=90,
            calibration_offset=0.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        self.fake_servo.angle_calls.reset_mock()

        s.reset()
        self.fake_servo.angle_calls.assert_called_with(0.0)

    def test_close_releases_servo_and_calls_close(self):
        s = ServoService(
            servo=self.fake_servo,
            name="closer",
            min_angle=-90,
            max_angle=90,
            calibration_offset=0.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        s.close()
        self.fake_servo.close_calls.assert_called_once()
        self.assertIsNone(s.servo)
        s.close()

    def test_get_default_calibration_function_raises_on_invalid_mode(self):
        s = ServoService(
            servo=self.fake_servo,
            name="badmode",
            min_angle=-90,
            max_angle=90,
            calibration_offset=0.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        with self.assertRaises(InvalidCalibrationModeError):
            s._get_default_calibration_function(object())  # type: ignore

    def test_repr_contains_key_fields(self):
        s = ServoService(
            servo=self.fake_servo,
            name="repr_name",
            min_angle=-10,
            max_angle=10,
            calibration_offset=0.5,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        r = repr(s)
        self.assertIn("repr_name", r)
        self.assertIn("0.5", r)

    def test_current_angle_property(self):
        s = ServoService(
            servo=self.fake_servo,
            name="prop",
            min_angle=-20,
            max_angle=20,
            calibration_offset=0.0,
            calibration_mode=ServoCalibrationMode.SUM,
        )
        self.assertEqual(s.current_angle, 0.0)
        s.current_angle = 7.5
        self.assertEqual(s.current_angle, 7.5)


if __name__ == "__main__":
    unittest.main()
