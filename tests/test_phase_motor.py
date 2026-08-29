import unittest
from unittest.mock import MagicMock, patch

from robot_hat import PhaseMotor


class TestPhaseMotor(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch("gpiozero.PhaseEnableMotor")
        self.addCleanup(patcher.stop)
        self.motor_class = patcher.start()
        self.backend = MagicMock()
        self.motor_class.return_value = self.backend

    def test_direction_and_offset_use_shared_calibration_contract(self) -> None:
        motor = PhaseMotor(
            phase_pin=5,
            enable_pin=12,
            calibration_direction=-1,
            calibration_speed_offset=10,
        )

        motor.set_speed(40)

        self.backend.backward.assert_called_once_with(0.5)
        self.assertEqual(motor.speed, 40)
        self.assertEqual(motor.applied_speed, -50)

    def test_zero_with_offset_stops(self) -> None:
        motor = PhaseMotor(
            phase_pin=5,
            enable_pin=12,
            calibration_speed_offset=10,
        )

        motor.set_speed(0)

        self.backend.stop.assert_called_once()
        self.backend.forward.assert_not_called()
        self.backend.backward.assert_not_called()


if __name__ == "__main__":
    unittest.main()
