import unittest
from unittest.mock import MagicMock

from robot_hat.exceptions import InvalidChannelName
from robot_hat.motor.i2c_dc_motor import I2CDCMotor


class TestI2CDCMotor(unittest.TestCase):
    def setUp(self):
        self.driver = MagicMock(spec=["set_pwm_freq", "set_pwm_duty_cycle", "close"])
        self.dir_pin = MagicMock(spec=["low", "high", "close"])

    def test_init_with_int_channel_sets_pwm_freq_and_uses_int_channel(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=5,
            frequency=60,
        )
        self.driver.set_pwm_freq.assert_called_once_with(60)
        self.assertEqual(motor.channel, 5)
        self.assertIn("Motor_5", motor.name)

    def test_init_with_string_channel_parses_and_sets_channel_and_name(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel="P3",
            frequency=50,
        )
        self.assertEqual(motor.channel, 3)
        self.assertEqual(motor.name, "Motor_P3")
        self.driver.set_pwm_freq.assert_called_once_with(50)

    def test_init_with_invalid_channel_string_raises(self):
        with self.assertRaises(InvalidChannelName):
            I2CDCMotor(
                dir_pin=self.dir_pin,
                driver=self.driver,
                channel="PX",
                frequency=50,
            )

    def test_set_speed_forward_calls_low_and_sets_duty_and_speed(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=0,
            frequency=50,
        )

        motor.set_speed(30)
        self.dir_pin.low.assert_called_once()
        self.dir_pin.high.assert_not_called()
        self.driver.set_pwm_duty_cycle.assert_called_once_with(0, 30)
        self.assertEqual(motor.speed, 30)

    def test_set_speed_reverse_calls_high_and_sets_duty_and_speed(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=1,
            frequency=50,
        )

        motor.set_speed(-40)
        self.dir_pin.high.assert_called_once()
        self.dir_pin.low.assert_not_called()
        self.driver.set_pwm_duty_cycle.assert_called_once_with(1, 40)
        self.assertEqual(motor.speed, -40)

    def test_set_speed_respects_calibration_direction_negative(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=2,
            calibration_direction=-1,
            frequency=50,
        )

        motor.set_speed(20)
        self.dir_pin.high.assert_called_once()
        self.driver.set_pwm_duty_cycle.assert_called_once_with(2, 20)
        self.assertEqual(motor.speed, -20)

    def test_set_speed_respects_speed_offset_update_non_persisted(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=3,
            calibration_speed_offset=0,
            frequency=50,
        )

        motor.update_calibration_speed(-10, persist=False)
        motor.set_speed(50)
        self.driver.set_pwm_duty_cycle.assert_called_once_with(3, 40)
        self.assertEqual(motor.speed, 40)

    def test_apply_speed_correction_clamps_and_scales_duty(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=4,
            max_speed=60,
            frequency=50,
        )

        motor.set_speed(100)
        self.driver.set_pwm_duty_cycle.assert_called_once_with(4, 100)
        self.assertEqual(motor.speed, 60)

        self.driver.reset_mock()
        self.dir_pin.reset_mock()
        motor.set_speed(-200)
        self.driver.set_pwm_duty_cycle.assert_called_once_with(4, 100)
        self.assertEqual(motor.speed, -60)
        self.dir_pin.high.assert_called_once()

    def test_stop_sets_duty_zero_and_speed_zero(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=7,
            frequency=50,
        )

        motor.set_speed(20)
        self.driver.reset_mock()
        motor.stop()
        self.driver.set_pwm_duty_cycle.assert_called_once_with(7, 0)
        self.assertEqual(motor.speed, 0)

    def test_close_closes_driver_and_pin(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=8,
            frequency=50,
        )

        motor.close()
        self.driver.close.assert_called_once()
        self.dir_pin.close.assert_called_once()

    def test_repr_includes_name_max_speed_and_current_speed(self):
        motor = I2CDCMotor(
            dir_pin=self.dir_pin,
            driver=self.driver,
            channel=9,
            max_speed=123,
            frequency=50,
        )
        motor.set_speed(42)
        rep = repr(motor)
        self.assertIn("Motor_9", rep)
        self.assertIn("max_speed=123", rep)
        self.assertIn("current_speed=42", rep)


if __name__ == "__main__":
    unittest.main()
