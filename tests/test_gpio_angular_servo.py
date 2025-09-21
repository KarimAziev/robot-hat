import unittest
from typing import Optional, cast
from unittest.mock import patch

from robot_hat import GPIOAngularServo


class FakeAngularServo:
    created_instances = []

    def __init__(self, pin, *args, **kwargs):
        self.pin = pin
        self.args = args
        self.kwargs = kwargs
        self.angle: Optional[float] = None
        self.closed = False
        FakeAngularServo.created_instances.append(self)

    def close(self):
        self.closed = True


class TestGPIOAngularServo(unittest.TestCase):
    def setUp(self):
        FakeAngularServo.created_instances.clear()

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_init_passes_parameters_to_gpiozero(self):
        pin = 17
        min_angle = -42.0
        max_angle = 44.0
        min_pulse = 1000
        max_pulse = 2000

        servo = GPIOAngularServo(
            pin=pin,
            min_angle=min_angle,
            max_angle=max_angle,
            min_pulse=min_pulse,
            max_pulse=max_pulse,
        )

        self.assertEqual(len(FakeAngularServo.created_instances), 1)
        inst = FakeAngularServo.created_instances[0]

        self.assertEqual(inst.pin, pin)

        expected_min_pulse_width = min_pulse / 1e6
        expected_max_pulse_width = max_pulse / 1e6

        self.assertIn("min_angle", inst.kwargs)
        self.assertIn("max_angle", inst.kwargs)
        self.assertIn("min_pulse_width", inst.kwargs)
        self.assertIn("max_pulse_width", inst.kwargs)

        self.assertEqual(inst.kwargs["min_angle"], min_angle)
        self.assertEqual(inst.kwargs["max_angle"], max_angle)
        self.assertAlmostEqual(inst.kwargs["min_pulse_width"], expected_min_pulse_width)
        self.assertAlmostEqual(inst.kwargs["max_pulse_width"], expected_max_pulse_width)

        self.assertEqual(servo.pin, pin)
        self.assertEqual(servo.min_angle, min_angle)
        self.assertEqual(servo.max_angle, max_angle)
        self.assertEqual(servo.min_pulse, min_pulse)
        self.assertEqual(servo.max_pulse, max_pulse)

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_angle_sets_and_clamps(self):
        servo = GPIOAngularServo(pin=5, min_angle=-10, max_angle=10)
        backend = servo._servo

        servo.angle(5)
        self.assertEqual(backend.angle, 5)

        servo.angle(20)
        self.assertEqual(backend.angle, 10)

        servo.angle(-20)
        self.assertEqual(backend.angle, -10)

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_pulse_width_time_maps_and_clamps(self):
        min_angle = -90
        max_angle = 90
        min_pulse = 1000
        max_pulse = 2000
        servo = GPIOAngularServo(
            pin=12,
            min_angle=min_angle,
            max_angle=max_angle,
            min_pulse=min_pulse,
            max_pulse=max_pulse,
        )
        backend = servo._servo

        mid_pulse = (min_pulse + max_pulse) / 2
        servo.pulse_width_time(mid_pulse)
        expected_mid = 0.0
        self.assertAlmostEqual(cast(float, backend.angle), expected_mid)

        quarter_pulse = min_pulse + 0.25 * (max_pulse - min_pulse)
        servo.pulse_width_time(quarter_pulse)
        expected_quarter = ((quarter_pulse - min_pulse) / (max_pulse - min_pulse)) * (
            max_angle - min_angle
        ) + min_angle
        self.assertAlmostEqual(cast(float, backend.angle), expected_quarter)

        servo.pulse_width_time(max_pulse + 500)
        self.assertAlmostEqual(cast(float, backend.angle), max_angle)

        servo.pulse_width_time(min_pulse - 500)
        self.assertAlmostEqual(cast(float, backend.angle), min_angle)

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_reset_sets_midpoint(self):
        min_angle = -30
        max_angle = 50
        servo = GPIOAngularServo(pin=9, min_angle=min_angle, max_angle=max_angle)
        backend = servo._servo

        servo.reset()
        expected_mid = (min_angle + max_angle) / 2
        self.assertIsNotNone(backend.angle)
        self.assertAlmostEqual(cast(float, backend.angle), expected_mid)

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_close_calls_backend_close(self):
        servo = GPIOAngularServo(pin=7)
        backend = servo._servo

        self.assertFalse(backend.closed)
        servo.close()
        self.assertTrue(backend.closed)

    @patch("gpiozero.AngularServo", new=FakeAngularServo)
    def test_context_manager_calls_close_on_exit(self):
        servo = GPIOAngularServo(pin=3)
        backend = servo._servo

        self.assertFalse(backend.closed)
        with servo:
            servo.angle(1)
            self.assertEqual(backend.angle, 1)
        self.assertTrue(backend.closed)


if __name__ == "__main__":
    unittest.main()
