import os
from unittest import TestCase, main
from unittest.mock import MagicMock, mock_open, patch

import robot_hat.utils as utils


class TestUtils(TestCase):
    def tearDown(self):
        for key in [
            "GPIOZERO_PIN_FACTORY",
            "PYGAME_HIDE_SUPPORT_PROMPT",
            "ROBOT_HAT_MOCK_SMBUS",
            "ROBOT_HAT_DISCHARGE_RATE",
        ]:
            os.environ.pop(key, None)

        try:
            utils.get_device_model.cache_clear()
        except AttributeError:
            pass

    def test_compose_no_functions(self):
        fn = utils.compose()
        self.assertEqual(fn(1), 1)
        self.assertEqual(fn(1, 2, 3), (1, 2, 3))

    def test_compose_chain(self):
        def add(a, b):
            return a + b

        def double(x):
            return x * 2

        def to_str(x):
            return f"val:{x}"

        composed = utils.compose(to_str, double, add)
        self.assertEqual(composed(3, 7), "val:20")

    def test_mapping_int_and_float(self):
        self.assertIsInstance(utils.mapping(5, 0, 10, 0, 100), int)
        self.assertEqual(utils.mapping(5, 0, 10, 0, 100), 50)
        res = utils.mapping(2.5, 0.0, 5.0, 0.0, 1.0)
        self.assertIsInstance(res, float)
        self.assertAlmostEqual(res, 0.5)

    def test_constrain(self):
        self.assertEqual(utils.constrain(5, 0, 10), 5)
        self.assertEqual(utils.constrain(-1, 0, 10), 0)
        self.assertEqual(utils.constrain(20, 0, 10), 10)

    def test_parse_int_suffix(self):
        self.assertEqual(utils.parse_int_suffix("sensor12"), 12)
        self.assertEqual(utils.parse_int_suffix("no_digits"), None)
        self.assertEqual(utils.parse_int_suffix("123"), 123)

    @patch(
        "builtins.open", new_callable=mock_open, read_data=b"Raspberry Pi 4 Model B\x00"
    )
    def test_is_raspberry_pi_true(self, mock_open_builtin):
        utils.get_device_model.cache_clear()
        self.assertTrue(utils.is_raspberry_pi())
        mock_open_builtin.assert_called_with("/proc/device-tree/model", "rb")

    @patch("builtins.open", side_effect=FileNotFoundError)
    def test_is_raspberry_pi_file_missing(self, _):
        utils.get_device_model.cache_clear()
        self.assertFalse(utils.is_raspberry_pi())

    @patch.object(utils, "get_device_model", return_value=None)
    def test_get_gpio_factory_name_no_model(self, _):
        self.assertEqual(utils.get_gpio_factory_name(), "mock")

    @patch.object(utils, "get_device_model", return_value="raspberry pi 5 model b")
    def test_get_gpio_factory_name_rpi5(self, _):
        self.assertEqual(utils.get_gpio_factory_name(), "lgpio")

    @patch.object(utils, "get_device_model", return_value="raspberry pi 4 model b")
    def test_get_gpio_factory_name_other_rpi(self, _):
        self.assertEqual(utils.get_gpio_factory_name(), "rpigpio")

    @patch("robot_hat.utils._log.exception")
    @patch("builtins.open", side_effect=RuntimeError("Test intentional error"))
    def test_get_device_model_unexpected_error(self, _, mock_log_exception: MagicMock):
        utils.get_device_model.cache_clear()
        self.assertIsNone(utils.get_device_model())
        mock_log_exception.assert_called_once()

    @patch(
        "builtins.open", new_callable=mock_open, read_data=b"Raspberry Pi 5 Model B\x00"
    )
    def test_get_device_model_success(self, mock_open_builtin):
        utils.get_device_model.cache_clear()
        self.assertEqual(utils.get_device_model(), "raspberry pi 5 model b")
        mock_open_builtin.assert_called_with("/proc/device-tree/model", "rb")

    @patch("builtins.open", side_effect=PermissionError)
    def test_get_device_model_permission_error(self, _):
        utils.get_device_model.cache_clear()
        self.assertIsNone(utils.get_device_model())

    def test_setup_env_vars_when_factory_set_by_get(self):
        with patch.object(utils, "get_gpio_factory_name", return_value="lgpio"):
            os.environ.pop("GPIOZERO_PIN_FACTORY", None)
            is_real = utils.setup_env_vars()
            self.assertTrue(is_real)
            self.assertEqual(os.environ.get("GPIOZERO_PIN_FACTORY"), "lgpio")
            self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
            self.assertIsNone(os.environ.get("ROBOT_HAT_MOCK_SMBUS"))
            self.assertIsNone(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"))

    def test_setup_env_vars_when_factory_is_mock(self):
        with patch.object(utils, "get_gpio_factory_name", return_value="mock"):
            os.environ.pop("GPIOZERO_PIN_FACTORY", None)
            is_real = utils.setup_env_vars()
            self.assertFalse(is_real)
            self.assertEqual(os.environ.get("GPIOZERO_PIN_FACTORY"), "mock")
            self.assertEqual(os.environ.get("PYGAME_HIDE_SUPPORT_PROMPT"), "1")
            self.assertEqual(os.environ.get("ROBOT_HAT_MOCK_SMBUS"), "1")
            self.assertEqual(os.environ.get("ROBOT_HAT_DISCHARGE_RATE"), "10")

    def test_setup_env_vars_when_gpiozero_already_set(self):
        os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"
        with patch.object(utils, "is_raspberry_pi", return_value=True) as mock_is_rpi:
            is_real = utils.setup_env_vars()
            self.assertTrue(is_real)
            self.assertEqual(os.environ["GPIOZERO_PIN_FACTORY"], "rpigpio")
            mock_is_rpi.assert_called_once()


if __name__ == "__main__":
    main()
