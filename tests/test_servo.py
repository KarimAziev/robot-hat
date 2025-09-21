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
            real_min_angle=0.0,
            real_max_angle=180.0,
            min_pulse=400,
            max_pulse=2600,
        )
        s.angle(0)
        self.driver.set_servo_pulse.assert_called_once_with(4, 1500)

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
        s = Servo(driver=self.driver, channel=7)
        s.close()
        self.driver.close.assert_called_once()

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
