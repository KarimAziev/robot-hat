import unittest

from robot_hat.exceptions import EnvironmentalSensorReadError, MagnetometerReadError
from robot_hat.mock.environmental_sensor import MockEnvironmentalSensor
from robot_hat.mock.magnetometer import MockMagnetometer


class TestMockAuxiliarySensors(unittest.TestCase):
    def test_environmental_sensor_is_deterministic_and_mutable(self) -> None:
        sensor = MockEnvironmentalSensor(monotonic_ns=lambda: 10)
        with self.assertRaises(EnvironmentalSensorReadError):
            sensor.read_sample()
        sensor.initialize()
        self.assertEqual(sensor.read_sample().pressure_pa, 101_325.0)
        sensor.set_sample(
            temperature_c=18.0,
            relative_humidity_percent=70.0,
            pressure_pa=None,
        )
        self.assertEqual(sensor.read_sample().temperature_c, 18.0)

    def test_magnetometer_is_deterministic_and_mutable(self) -> None:
        sensor = MockMagnetometer(monotonic_ns=lambda: 11)
        with self.assertRaises(MagnetometerReadError):
            sensor.read_sample()
        sensor.initialize()
        sensor.set_sample((1e-6, 2e-6, 3e-6))
        self.assertEqual(sensor.read_sample().magnetic_field_t, (1e-6, 2e-6, 3e-6))


if __name__ == "__main__":
    unittest.main()
