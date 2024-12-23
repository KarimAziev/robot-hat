import os
import unittest
from unittest.mock import MagicMock, patch

from robot_hat.exceptions import (
    InvalidPin,
    InvalidPinInterruptTrigger,
    InvalidPinMode,
    InvalidPinName,
    InvalidPinNumber,
    InvalidPinPull,
)
from robot_hat.pin import Pin


class TestPin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the mock GPIO environment for all tests."""
        os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

    def setUp(self):
        """Setup a sample pin mapping for the tests."""
        self.pin_mapping = {
            "D0": 17,
            "D1": 4,
            "D2": 27,
        }

    def test_pin_value_set_high(self):
        """Test setting a pin value to high."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)

        result = pin.value(1)

        self.assertEqual(result, 1)
        self.assertIsNotNone(pin.gpio)
        if pin.gpio:
            self.assertTrue(pin.gpio.value)

    def test_pin_value_set_low(self):
        """Test setting a pin value to low."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)

        self.assertIsNotNone(pin.gpio)

        result = pin.value(0)

        self.assertEqual(result, 0)
        if pin.gpio:
            self.assertFalse(pin.gpio.value)

    def test_pin_initialization_with_number(self):
        """Test initializing a Pin object with a valid pin number."""
        pin = Pin(17, pin_dict=self.pin_mapping)
        self.assertEqual(pin._pin_num, 17)
        self.assertEqual(pin._board_name, "D0")

    @patch("robot_hat.pin.logger")
    def test_pin_invalid_name(self, mock_logger: MagicMock):
        """Test initializing a Pin object with an invalid name."""
        with self.assertRaises(InvalidPinName):
            Pin("D99", pin_dict=self.pin_mapping)
        mock_logger.error.assert_called_once()

    def test_pin_invalid_number(self):
        """Test initializing a Pin object with an invalid number."""
        with self.assertRaises(InvalidPinNumber):
            Pin(99, pin_dict=self.pin_mapping)

    @patch("robot_hat.pin.logger")
    def test_pin_invalid_type(self, mock_logger: MagicMock):
        """Test initializing a Pin object with an unsupported type."""
        with self.assertRaises(InvalidPin):
            Pin(None, pin_dict=self.pin_mapping)  # type: ignore

        mock_logger.error.assert_called_once_with('Invalid PIN: "None"')

    @patch("gpiozero.OutputDevice")
    def test_pin_setup_as_output(self, mock_output_device):
        """Test setting up a pin as output."""
        pin = Pin("D0", pin_dict=self.pin_mapping)
        pin.setup(mode=Pin.OUT)
        self.assertEqual(pin._mode, Pin.OUT)
        mock_output_device.assert_called_with(17)

    @patch("gpiozero.InputDevice")
    def test_pin_setup_as_input_with_pull_up(self, mock_input_device):
        """Test setting up a pin as input with pull-up resistor."""
        pin = Pin("D0", pin_dict=self.pin_mapping)
        pin.setup(mode=Pin.IN, pull=Pin.PULL_UP)
        self.assertEqual(pin._mode, Pin.IN)
        self.assertEqual(pin._pull, Pin.PULL_UP)
        mock_input_device.assert_called_with(17, pull_up=True)

    @patch("robot_hat.pin.logger")
    def test_pin_invalid_mode(self, mock_logger: MagicMock):
        """Test setting up a pin with an invalid mode."""
        pin = Pin("D0", pin_dict=self.pin_mapping)
        with self.assertRaises(InvalidPinMode):
            pin.setup(mode=0x99)
        mock_logger.error.assert_called_once()

    @patch("robot_hat.pin.logger")
    def test_pin_invalid_pull(self, mock_logger: MagicMock):
        """Test setting up a pin with an invalid pull configuration."""
        pin = Pin("D0", pin_dict=self.pin_mapping)
        with self.assertRaises(InvalidPinPull):
            pin.setup(mode=Pin.IN, pull=0x99)
        mock_logger.error.assert_called_once()

    @patch("gpiozero.InputDevice", spec=True)
    def test_pin_value_get(self, mock_input_device):
        """Test getting a pin value."""
        mock_gpio = MagicMock()
        mock_gpio.value = 1
        mock_input_device.return_value = mock_gpio

        pin = Pin("D0", mode=Pin.IN, pin_dict=self.pin_mapping)
        result = pin.value()
        self.assertEqual(result, 1)

    def test_pin_on(self):
        """Test turning a pin on."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)
        with patch.object(pin, "value", return_value=1) as mock_value:
            result = pin.on()
            self.assertEqual(result, 1)
            mock_value.assert_called_once_with(1)

    def test_pin_off(self):
        """Test turning a pin off."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)
        with patch.object(pin, "value", return_value=0) as mock_value:
            result = pin.off()
            self.assertEqual(result, 0)
            mock_value.assert_called_once_with(0)

    def test_pin_irq_invalid_trigger(self):
        """Test setting an interrupt with an invalid trigger."""
        pin = Pin("D0", pin_dict=self.pin_mapping)
        with self.assertRaises(InvalidPinInterruptTrigger):
            pin.irq(handler=lambda: None, trigger=0x99)

    def test_pin_close(self):
        """Test closing a pin."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)
        pin.gpio = MagicMock()
        pin.close()
        pin.gpio.close.assert_called_once()

    def test_pin_deinit(self):
        """Test deinitializing a pin."""
        pin = Pin("D0", mode=Pin.OUT, pin_dict=self.pin_mapping)
        pin.gpio = MagicMock()
        pin.gpio.pin_factory = MagicMock()
        pin.deinit()
        pin.gpio.close.assert_called_once()
        pin.gpio.pin_factory.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
