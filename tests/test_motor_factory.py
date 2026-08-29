import unittest
from unittest.mock import MagicMock, patch

from robot_hat import I2CDCMotorConfig, MotorFactory, PWMDriverConfig


class TestMotorFactoryOwnership(unittest.TestCase):
    def setUp(self) -> None:
        self.config = I2CDCMotorConfig(
            calibration_direction=-1,
            name="left",
            max_speed=80,
            driver=PWMDriverConfig(
                name="PCA9685",
                bus=1,
                address=0x40,
                frame_width=20000,
                freq=50,
            ),
            channel=3,
            dir_pin="D4",
        )

    @patch("robot_hat.factories.motor_factory.I2CDCMotor")
    @patch("robot_hat.factories.motor_factory.Pin")
    @patch("robot_hat.factories.motor_factory.PWMFactory.create_pwm_driver")
    def test_factory_owns_resources_it_creates(
        self,
        create_driver: MagicMock,
        pin_class: MagicMock,
        motor_class: MagicMock,
    ) -> None:
        driver = create_driver.return_value
        pin = pin_class.return_value

        MotorFactory.create_i2c_motor(self.config)

        motor_class.assert_called_once_with(
            channel=3,
            driver=driver,
            frequency=50,
            dir_pin=pin,
            calibration_direction=-1,
            max_speed=80,
            owns_driver=True,
            owns_direction_pin=True,
        )

    @patch("robot_hat.factories.motor_factory.I2CDCMotor")
    @patch("robot_hat.factories.motor_factory.Pin")
    @patch("robot_hat.factories.motor_factory.PWMFactory.create_pwm_driver")
    def test_factory_does_not_own_injected_resources(
        self,
        create_driver: MagicMock,
        pin_class: MagicMock,
        motor_class: MagicMock,
    ) -> None:
        driver = MagicMock()
        pin = MagicMock()

        MotorFactory.create_i2c_motor(self.config, driver=driver, dir_pin=pin)

        create_driver.assert_not_called()
        pin_class.assert_not_called()
        self.assertFalse(motor_class.call_args.kwargs["owns_driver"])
        self.assertFalse(motor_class.call_args.kwargs["owns_direction_pin"])

    @patch("robot_hat.factories.motor_factory.Pin", side_effect=RuntimeError("pin"))
    @patch("robot_hat.factories.motor_factory.PWMFactory.create_pwm_driver")
    def test_factory_closes_created_driver_when_construction_fails(
        self, create_driver: MagicMock, _pin_class: MagicMock
    ) -> None:
        with self.assertRaisesRegex(RuntimeError, "pin"):
            MotorFactory.create_i2c_motor(self.config)

        create_driver.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
