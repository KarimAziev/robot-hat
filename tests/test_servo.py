import unittest
from unittest.mock import Mock

from robot_hat.exceptions import InvalidChannelName
from robot_hat.servos.servo import Servo


class TestServo(unittest.TestCase):
    def setUp(self):
        self.driver = Mock(spec=["set_servo_pulse", "close"])

    def test_channel_as_int_sets_name_and_channel(self):
        s = Servo(driver=self.driver, channel=3)
        self.assertEqual(s.channel, 3)
        self.assertEqual(s.name, "P3")

    def test_channel_as_string_parsed_and_name_kept(self):
        s = Servo(driver=self.driver, channel="CHAN10")
        self.assertEqual(s.channel, 10)
        self.assertEqual(s.name, "CHAN10")

    def test_invalid_channel_name_raises(self):
        with self.assertRaises(InvalidChannelName):
            Servo(driver=self.driver, channel="NO_DIGITS")

    def test_angle_middle_maps_to_middle_pulse(self):
        s = Servo(driver=self.driver, channel=0)
        s.angle(0)
        self.driver.set_servo_pulse.assert_called_once_with(0, 1500)

    def test_angle_clamps_below_min(self):
        s = Servo(driver=self.driver, channel=1)
        s.angle(-180)
        self.driver.set_servo_pulse.assert_called_once_with(1, 500)

    def test_angle_clamps_above_max(self):
        s = Servo(driver=self.driver, channel=2)
        s.angle(180)
        self.driver.set_servo_pulse.assert_called_once_with(2, 2500)

    def test_angle_with_different_real_range(self):
        s = Servo(
            driver=self.driver,
            channel=4,
            min_angle=0.0,
            max_angle=180.0,
            real_min_angle=0.0,
            real_max_angle=180.0,
            min_pulse=400,
            max_pulse=2600,
        )
        s.angle(0)
        self.driver.set_servo_pulse.assert_called_once_with(4, 400)
        s.angle(90)
        self.driver.set_servo_pulse.assert_called_with(4, 1500)

    def test_travel_limits_do_not_rescale_pulse_calibration(self):
        for limit, expected in ((30, (1267, 1733)), (10, (1422, 1578))):
            with self.subTest(limit=limit):
                servo = Servo(
                    driver=self.driver,
                    channel=11,
                    min_angle=-limit,
                    max_angle=limit,
                    min_pulse=800,
                    max_pulse=2200,
                )
                servo.angle(-100)
                self.driver.set_servo_pulse.assert_called_with(11, expected[0])
                servo.angle(100)
                self.driver.set_servo_pulse.assert_called_with(11, expected[1])
                servo.angle(5)
                self.driver.set_servo_pulse.assert_called_with(11, 1539)

    def test_measured_calibration_endpoints_define_degrees(self):
        servo = Servo(
            driver=self.driver,
            channel=11,
            min_angle=-10,
            max_angle=15,
            real_min_angle=-45,
            real_max_angle=45,
            min_pulse=1000,
            max_pulse=2000,
        )
        servo.angle(-30)
        self.driver.set_servo_pulse.assert_called_with(11, 1389)
        servo.angle(30)
        self.driver.set_servo_pulse.assert_called_with(11, 1667)

    def test_angle_never_exceeds_calibrated_pulse_range(self):
        servo = Servo(self.driver, 0, real_min_angle=-20, real_max_angle=20)
        servo.angle(-90)
        self.driver.set_servo_pulse.assert_called_with(0, 500)
        servo.angle(90)
        self.driver.set_servo_pulse.assert_called_with(0, 2500)

    def test_equal_travel_limits_hold_one_angle(self):
        servo = Servo(self.driver, 0, min_angle=0, max_angle=0)
        servo.angle(50)
        self.driver.set_servo_pulse.assert_called_with(0, 1500)

    def test_invalid_configuration_is_rejected_without_writes(self):
        for lower, upper in ((20, 10), (float("nan"), 90)):
            with self.assertRaises(ValueError):
                Servo(self.driver, 0, min_angle=lower, max_angle=upper)
        for lower, upper in ((10, 10), (20, 10), (-90, float("inf"))):
            with self.assertRaises(ValueError):
                Servo(self.driver, 0, real_min_angle=lower, real_max_angle=upper)
        for lower, upper in ((0, 2000), (2000, 1000), (1500, 1500)):
            with self.assertRaises(ValueError):
                Servo(self.driver, 0, min_pulse=lower, max_pulse=upper)
        self.driver.set_servo_pulse.assert_not_called()

    def test_non_finite_commands_are_rejected_without_writes(self):
        servo = Servo(self.driver, 0)
        for value in (float("nan"), float("inf"), float("-inf")):
            for command in (servo.angle, servo.pulse_width_time):
                with (
                    self.subTest(value=value, command=command),
                    self.assertRaises(ValueError),
                ):
                    command(value)
        self.driver.set_servo_pulse.assert_not_called()

    def test_closed_servo_cannot_write_to_shared_driver(self):
        servo = Servo(self.driver, 0)
        servo.close()
        for command in (servo.angle, servo.pulse_width_time):
            with self.assertRaises(RuntimeError):
                command(0)
        self.driver.set_servo_pulse.assert_not_called()

    def test_pulse_width_time_sets_direct_pulse_and_clamps(self):
        s = Servo(driver=self.driver, channel=5)
        s.pulse_width_time(2000.6)
        self.driver.set_servo_pulse.assert_called_once_with(5, 2001)

        self.driver.reset_mock()
        s.pulse_width_time(100.0)
        self.driver.set_servo_pulse.assert_called_once_with(5, 500)

        self.driver.reset_mock()
        s.pulse_width_time(10000.0)
        self.driver.set_servo_pulse.assert_called_once_with(5, 2500)

    def test_reset_calls_angle_zero(self):
        s = Servo(driver=self.driver, channel=6)
        s.reset()
        self.driver.set_servo_pulse.assert_called_once_with(6, 1500)

    def test_close_calls_driver_close(self):
        s = Servo(driver=self.driver, channel=7, owns_driver=True)
        s.close()
        s.close()
        self.driver.close.assert_called_once()

    def test_close_leaves_injected_driver_open_by_default(self):
        s = Servo(driver=self.driver, channel=7)

        s.close()
        s.close()

        self.driver.close.assert_not_called()

    def test_repr_contains_expected_information(self):
        s = Servo(
            driver=self.driver,
            channel=8,
            min_angle=-30,
            max_angle=30,
            min_pulse=600,
            max_pulse=2200,
        )
        r = repr(s)
        self.assertIn("channel=8", r)
        self.assertIn("angle_range=(-30", r)
        self.assertIn("pulse_range=(600, 2200)", r)


if __name__ == "__main__":
    unittest.main()
