import unittest
from unittest.mock import Mock, patch

from robot_hat.data_types.bus import BusType
from robot_hat.data_types.config.pwm import PWMDriverConfig
from robot_hat.factories.pwm_factory import (
    PWM_DRIVER_REGISTRY,
    PWMFactory,
    register_pwm_driver,
)
from robot_hat.interfaces.pwm_driver_abc import PWMDriverABC


class MockPWMDriver(PWMDriverABC):
    """Mock PWM driver for testing."""

    DRIVER_TYPE = "MockDriver"

    def __init__(self, bus: BusType, address=0x40, frame_width=20000):
        super().__init__(bus=bus, address=address)
        self.frame_width = frame_width

    def set_pwm_freq(self, freq: int) -> None:
        pass

    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        pass

    def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
        pass


class AnotherMockPWMDriver(PWMDriverABC):
    """Another mock PWM driver for testing."""

    DRIVER_TYPE = "AnotherMockDriver"

    def __init__(self, bus: BusType, address=0x40, frame_width=20000):
        super().__init__(bus=bus, address=address)
        self.frame_width = frame_width

    def set_pwm_freq(self, freq: int) -> None:
        pass

    def set_servo_pulse(self, channel: int, pulse: int) -> None:
        pass

    def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
        pass


class TestPWMFactory(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        import os

        os.environ["ROBOT_HAT_MOCK_SMBUS"] = "1"

        self.config = PWMDriverConfig(
            name="MockDriver",
            bus=1,
            address=0x40,
            frame_width=20000,
            freq=50,
        )

    def tearDown(self):
        """Clean up after tests."""
        PWM_DRIVER_REGISTRY.clear()

    def test_register_pwm_driver_decorator(self):
        """Test the register_pwm_driver decorator."""

        @register_pwm_driver
        class TestDriver(PWMDriverABC):
            DRIVER_TYPE = "TestDriver"

            def __init__(self, bus: BusType, address=0x40, frame_width=20000):
                super().__init__(bus=bus, address=address)
                self.frame_width = frame_width

            def set_pwm_freq(self, freq: int) -> None:
                pass

            def set_servo_pulse(self, channel: int, pulse: int) -> None:
                pass

            def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
                pass

        self.assertIn("TestDriver", PWM_DRIVER_REGISTRY)
        self.assertEqual(PWM_DRIVER_REGISTRY["TestDriver"], TestDriver)

    def test_register_pwm_driver_without_driver_type(self):
        """Test that register_pwm_driver raises ValueError without DRIVER_TYPE."""
        with self.assertRaises(ValueError) as context:

            @register_pwm_driver
            class InvalidDriver(PWMDriverABC):
                def __init__(self):
                    pass

                def set_pwm_freq(self, freq: int) -> None:
                    pass

                def set_servo_pulse(self, channel: int, pulse: int) -> None:
                    pass

                def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
                    pass

        self.assertIn(
            "must define a DRIVER_TYPE class attribute", str(context.exception)
        )

    def test_register_pwm_driver_returns_class(self):
        """Test that register_pwm_driver returns the class."""

        @register_pwm_driver
        class TestDriver(PWMDriverABC):
            DRIVER_TYPE = "TestDriver"

            def __init__(self):
                pass

            def set_pwm_freq(self, freq: int) -> None:
                pass

            def set_servo_pulse(self, channel: int, pulse: int) -> None:
                pass

            def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
                pass

        self.assertEqual(TestDriver.__name__, "TestDriver")

    def test_create_pwm_driver_with_registered_driver(self):
        """Test creating a PWM driver with a registered driver."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        with patch("robot_hat.factories.pwm_factory._log") as mock_log:
            driver = PWMFactory.create_pwm_driver(self.config)

            self.assertIsInstance(driver, MockPWMDriver)
            self.assertIsInstance(driver.bus, type(driver._bus))
            self.assertEqual(driver.address, 0x40)
            self.assertEqual(driver.frame_width, 20000)  # type: ignore

            mock_log.debug.assert_called()

    def test_create_pwm_driver_with_custom_bus(self):
        """Test creating a PWM driver with a custom bus."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        custom_bus = 2
        driver = PWMFactory.create_pwm_driver(self.config, bus=custom_bus)

        self.assertIsInstance(driver, MockPWMDriver)
        self.assertIsInstance(driver.bus, type(driver._bus))

    def test_create_pwm_driver_with_none_bus(self):
        """Test creating a PWM driver with None bus (uses config bus)."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        driver = PWMFactory.create_pwm_driver(self.config, bus=None)

        self.assertIsInstance(driver, MockPWMDriver)
        self.assertIsInstance(driver.bus, type(driver._bus))

    def test_create_pwm_driver_dynamic_import(self):
        """Test that create_pwm_driver dynamically imports PWM drivers."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        with patch("builtins.__import__") as mock_import:
            PWMFactory.create_pwm_driver(self.config)

            mock_import.assert_called()

    def test_create_pwm_driver_key_error(self):
        """Test that create_pwm_driver raises KeyError for unregistered driver."""
        unregistered_config = PWMDriverConfig(
            name="UnregisteredDriver",
            bus=1,
            address=0x40,
            frame_width=20000,
            freq=50,
        )

        with self.assertRaises(KeyError):
            PWMFactory.create_pwm_driver(unregistered_config)

    def test_pwm_driver_registry_independence(self):
        """Test that different driver types are stored independently."""
        PWM_DRIVER_REGISTRY["Driver1"] = MockPWMDriver
        PWM_DRIVER_REGISTRY["Driver2"] = AnotherMockPWMDriver

        self.assertEqual(len(PWM_DRIVER_REGISTRY), 2)
        self.assertEqual(PWM_DRIVER_REGISTRY["Driver1"], MockPWMDriver)
        self.assertEqual(PWM_DRIVER_REGISTRY["Driver2"], AnotherMockPWMDriver)

    def test_pwm_driver_registry_overwrite(self):
        """Test that registering a driver with the same name overwrites."""
        PWM_DRIVER_REGISTRY["TestDriver"] = MockPWMDriver

        PWM_DRIVER_REGISTRY["TestDriver"] = AnotherMockPWMDriver

        self.assertEqual(len(PWM_DRIVER_REGISTRY), 1)
        self.assertEqual(PWM_DRIVER_REGISTRY["TestDriver"], AnotherMockPWMDriver)

    def test_create_pwm_driver_logging_details(self):
        """Test that create_pwm_driver logs correct details."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        with patch("robot_hat.factories.pwm_factory._log") as mock_log:
            PWMFactory.create_pwm_driver(self.config)

            mock_log.debug.assert_called_once()
            call_args = mock_log.debug.call_args
            self.assertIn("MockDriver", str(call_args))
            self.assertIn("0x40", str(call_args))
            self.assertIn("20000", str(call_args))

    def test_create_pwm_driver_with_bus_object(self):
        """Test creating a PWM driver with a bus object instead of int."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        mock_bus = Mock()
        driver = PWMFactory.create_pwm_driver(self.config, bus=mock_bus)

        self.assertIsInstance(driver, MockPWMDriver)
        self.assertEqual(driver.bus, mock_bus)

    def test_create_pwm_driver_preserves_config_values(self):
        """Test that create_pwm_driver preserves all config values."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        driver = PWMFactory.create_pwm_driver(self.config)

        self.assertIsInstance(driver.bus, type(driver._bus))
        self.assertEqual(driver.address, self.config.address)
        self.assertEqual(driver.frame_width, self.config.frame_width)  # type: ignore

    def test_pwm_driver_registry_global_state(self):
        """Test that PWM_DRIVER_REGISTRY is a global state."""
        PWM_DRIVER_REGISTRY.clear()

        PWM_DRIVER_REGISTRY["TestDriver"] = MockPWMDriver

        from robot_hat.factories.pwm_factory import (
            PWM_DRIVER_REGISTRY as imported_registry,
        )

        self.assertIn("TestDriver", imported_registry)
        self.assertEqual(imported_registry["TestDriver"], MockPWMDriver)

    def test_register_pwm_driver_multiple_times(self):
        """Test registering the same driver multiple times."""

        @register_pwm_driver
        class TestDriver(PWMDriverABC):
            DRIVER_TYPE = "TestDriver"

            def __init__(self):
                pass

            def set_pwm_freq(self, freq: int) -> None:
                pass

            def set_servo_pulse(self, channel: int, pulse: int) -> None:
                pass

            def set_pwm_duty_cycle(self, channel: int, duty: int) -> None:
                pass

        PWM_DRIVER_REGISTRY["TestDriver"] = TestDriver

        self.assertEqual(PWM_DRIVER_REGISTRY["TestDriver"], TestDriver)

    def test_create_pwm_driver_with_different_configs(self):
        """Test creating PWM drivers with different configurations."""
        PWM_DRIVER_REGISTRY["MockDriver"] = MockPWMDriver

        config1 = PWMDriverConfig(
            name="MockDriver",
            bus=1,
            address=0x40,
            frame_width=20000,
            freq=50,
        )

        config2 = PWMDriverConfig(
            name="MockDriver",
            bus=2,
            address=0x41,
            frame_width=15000,
            freq=100,
        )

        driver1 = PWMFactory.create_pwm_driver(config1)
        driver2 = PWMFactory.create_pwm_driver(config2)

        self.assertIsNot(driver1, driver2)
        self.assertIsInstance(driver1.bus, type(driver1._bus))
        self.assertIsInstance(driver2.bus, type(driver2._bus))
        self.assertEqual(driver1.address, 0x40)
        self.assertEqual(driver2.address, 0x41)


if __name__ == "__main__":
    unittest.main()
