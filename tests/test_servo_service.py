import unittest
from unittest.mock import patch

from robot_hat import ServoCalibrationMode, ServoService


class TestServoService(unittest.TestCase):
    def setUp(self):
        self.servo_patch = patch("robot_hat.services.servo_service.Servo")
        self.MockServo = self.servo_patch.start()
        self.mock_servo_instance = self.MockServo.return_value

    def tearDown(self):
        self.servo_patch.stop()

    def test_initialization(self):
        service = ServoService(
            servo_pin="P2",
            min_angle=-45,
            max_angle=45,
            calibration_offset=5,
            calibration_mode=ServoCalibrationMode.NEGATIVE,
        )
        self.assertEqual(service.min_angle, -45)
        self.assertEqual(service.max_angle, 45)
        self.assertEqual(service.calibration_offset, 5)
        self.assertEqual(service._persisted_calibration_offset, 5)
        self.assertEqual(service.current_angle, 0.0)
        self.assertEqual(service.name, "P2")

    def test_set_angle_with_constraints(self):
        service = ServoService(
            servo_pin="P1", min_angle=-45, max_angle=45, calibration_mode=None
        )

        service.set_angle(30)
        self.mock_servo_instance.angle.assert_called_with(30)
        self.assertEqual(service.current_angle, 30)

        service.set_angle(100)
        self.mock_servo_instance.angle.assert_called_with(45)
        self.assertEqual(service.current_angle, 45)

        service.set_angle(-100)
        self.mock_servo_instance.angle.assert_called_with(-45)
        self.assertEqual(service.current_angle, -45)

    def test_set_angle_with_constraints_with_negative_calibration(self):
        service = ServoService(servo_pin="P1", min_angle=-45, max_angle=45)

        service.set_angle(30)
        self.mock_servo_instance.angle.assert_called_with(30)
        self.assertEqual(service.current_angle, 30)

        service.set_angle(100)
        self.mock_servo_instance.angle.assert_called_with(100)
        self.assertEqual(service.current_angle, 45)

        service.set_angle(-100)
        self.mock_servo_instance.angle.assert_called_with(-100)
        self.assertEqual(service.current_angle, -45)

    def test_set_angle_with_calibration_sum_mode(self):
        service = ServoService(
            servo_pin="P1",
            min_angle=-45,
            max_angle=45,
            calibration_offset=5,
            calibration_mode=ServoCalibrationMode.SUM,
        )

        service.set_angle(30)
        self.mock_servo_instance.angle.assert_called_with(35)  # 30 + 5
        self.assertEqual(service.current_angle, 30)

    def test_set_angle_with_calibration_negative_mode(self):
        service = ServoService(
            servo_pin="P1",
            min_angle=-45,
            max_angle=45,
            calibration_offset=5,
            calibration_mode=ServoCalibrationMode.NEGATIVE,
        )

        service.set_angle(30)
        self.mock_servo_instance.angle.assert_called_with(-25)
        self.assertEqual(service.current_angle, 30)

    def test_set_angle_with_no_calibration(self):
        service = ServoService(
            servo_pin="P1",
            min_angle=-45,
            max_angle=45,
            calibration_mode=None,
        )

        service.set_angle(20)
        self.mock_servo_instance.angle.assert_called_with(20)
        self.assertEqual(service.current_angle, 20)

    def test_update_calibration(self):
        service = ServoService(servo_pin="P1", calibration_offset=10)

        updated_offset = service.update_calibration(15)
        self.assertEqual(updated_offset, 15)
        self.assertEqual(service.calibration_offset, 15)
        self.assertEqual(service._persisted_calibration_offset, 10)

        updated_offset = service.update_calibration(20, persist=True)
        self.assertEqual(updated_offset, 20)
        self.assertEqual(service.calibration_offset, 20)
        self.assertEqual(service._persisted_calibration_offset, 20)

    def test_reset_calibration(self):
        service = ServoService(servo_pin="P1", calibration_offset=10)
        service.update_calibration(15)
        self.assertEqual(service.calibration_offset, 15)

        reset_offset = service.reset_calibration()
        self.assertEqual(reset_offset, 10)
        self.assertEqual(service.calibration_offset, 10)

    def test_reset(self):
        service = ServoService(servo_pin="P1")
        service.set_angle(30)
        self.assertEqual(service.current_angle, 30)

        service.reset()
        self.mock_servo_instance.angle.assert_called_with(0)
        self.assertEqual(service.current_angle, 0)

    def test_apply_sum_calibration(self):
        result = ServoService.apply_sum_calibration(30, 5)
        self.assertEqual(result, 35)

    def test_apply_negative_calibration(self):
        result = ServoService.apply_negative_calibration(30, 5)
        self.assertEqual(result, -25)
        result = ServoService.apply_negative_calibration(30, -14.4)
        self.assertEqual(result, -44.4)

    def test_repr(self):
        service = ServoService(
            servo_pin="P1", min_angle=-45, max_angle=45, calibration_offset=5
        )

        self.assertIn("Servo", repr(service))
        self.assertIn("min_angle=-45", repr(service))
        self.assertIn("max_angle=45", repr(service))
        self.assertIn("calibration_offset=5", repr(service))
        self.assertIn("name=P1", repr(service))


if __name__ == "__main__":
    unittest.main()
