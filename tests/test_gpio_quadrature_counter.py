import unittest
from unittest.mock import Mock, patch

from robot_hat.data_types.quadrature import QuadratureDecodeMode
from robot_hat.drivers.gpio.gpiozero_digital_edge_input import (
    GPIOZeroDigitalEdgeInput,
)
from robot_hat.exceptions import EncoderClosedError, EncoderNotInitializedError
from robot_hat.interfaces.digital_edge_input_abc import (
    DigitalEdgeCallback,
    DigitalEdgeInputABC,
)
from robot_hat.sensors.encoder.gpio_quadrature_counter import (
    GPIOQuadratureCounterBackend,
)


class FakeDigitalEdgeInput(DigitalEdgeInputABC):
    def __init__(self, initial: bool = False) -> None:
        self.value = initial
        self.callback: DigitalEdgeCallback | None = None
        self.initialized = False
        self.closed = False
        self.read_error: Exception | None = None

    def initialize(self) -> None:
        if self.closed:
            raise EncoderClosedError("fake input is closed")
        self.initialized = True

    def read(self) -> bool:
        if self.closed:
            raise EncoderClosedError("fake input is closed")
        if not self.initialized:
            raise EncoderNotInitializedError("fake input is not initialized")
        if self.read_error is not None:
            raise self.read_error
        return self.value

    def set_edge_callback(self, callback: DigitalEdgeCallback | None) -> None:
        if self.closed:
            raise EncoderClosedError("fake input is closed")
        self.callback = callback

    def set_level(self, value: bool) -> None:
        changed = value != self.value
        self.value = value
        if changed and self.callback is not None:
            self.callback()

    def close(self) -> None:
        self.callback = None
        self.initialized = False
        self.closed = True


class TestGPIOQuadratureCounterBackend(unittest.TestCase):
    def setUp(self) -> None:
        self.a = FakeDigitalEdgeInput()
        self.b = FakeDigitalEdgeInput()
        self.backend = GPIOQuadratureCounterBackend(
            a_input=self.a,
            b_input=self.b,
            monotonic_ns=lambda: 123,
        )

    def test_decodes_forward_and_reverse_both_edge_sequences(self) -> None:
        self.backend.initialize()

        self.b.set_level(True)
        self.a.set_level(True)
        self.b.set_level(False)
        self.a.set_level(False)
        self.assertEqual(self.backend.read_snapshot().count, 4)

        self.a.set_level(True)
        self.b.set_level(True)
        self.a.set_level(False)
        self.b.set_level(False)
        snapshot = self.backend.read_snapshot()
        self.assertEqual(snapshot.count, 0)
        self.assertEqual(snapshot.timestamp_monotonic_ns, 123)

    def test_supports_decode_mode_reset_and_idempotent_initialize(self) -> None:
        backend = GPIOQuadratureCounterBackend(
            a_input=self.a,
            b_input=self.b,
            decode_mode=QuadratureDecodeMode.X1,
        )
        backend.initialize()
        backend.initialize()
        self.b.set_level(True)
        self.a.set_level(True)
        self.b.set_level(False)
        self.a.set_level(False)
        self.assertEqual(backend.read_snapshot().count, 1)

        backend.reset(-7)
        self.assertEqual(backend.read_snapshot().count, -7)

    def test_callback_read_failure_becomes_invalid_transition_diagnostic(self) -> None:
        self.backend.initialize()
        self.a.read_error = OSError("injected")

        with self.assertLogs(
            "robot_hat.sensors.encoder.gpio_quadrature_counter", level="WARNING"
        ):
            self.b.set_level(True)

        self.a.read_error = None
        self.assertEqual(self.backend.read_snapshot().invalid_transitions, 1)

    def test_owns_inputs_by_default_and_detaches_shared_inputs(self) -> None:
        self.backend.initialize()
        self.backend.close()
        self.backend.close()
        self.assertTrue(self.a.closed)
        self.assertTrue(self.b.closed)
        with self.assertRaises(EncoderClosedError):
            self.backend.read_snapshot()

        shared_a = FakeDigitalEdgeInput()
        shared_b = FakeDigitalEdgeInput()
        shared = GPIOQuadratureCounterBackend(
            a_input=shared_a,
            b_input=shared_b,
            owns_inputs=False,
        )
        shared.initialize()
        shared.close()
        self.assertFalse(shared_a.closed)
        self.assertFalse(shared_b.closed)
        self.assertIsNone(shared_a.callback)
        self.assertIsNone(shared_b.callback)

    def test_rejects_reads_before_initialization_and_same_input(self) -> None:
        with self.assertRaises(EncoderNotInitializedError):
            self.backend.read_snapshot()
        with self.assertRaises(ValueError):
            GPIOQuadratureCounterBackend(a_input=self.a, b_input=self.a)


class TestGPIOZeroDigitalEdgeInput(unittest.TestCase):
    def test_opens_without_debounce_attaches_both_edges_and_closes(self) -> None:
        device = Mock()
        device.value = 1
        with patch("gpiozero.DigitalInputDevice", return_value=device) as factory:
            edge_input = GPIOZeroDigitalEdgeInput("GPIO17", pull_up=True)
            callback = Mock()
            edge_input.set_edge_callback(callback)
            edge_input.initialize()

        factory.assert_called_once_with(
            "GPIO17",
            pull_up=True,
            active_state=None,
            bounce_time=None,
        )
        self.assertIs(device.when_activated, callback)
        self.assertIs(device.when_deactivated, callback)
        self.assertTrue(edge_input.read())

        edge_input.close()
        edge_input.close()
        self.assertIsNone(device.when_activated)
        self.assertIsNone(device.when_deactivated)
        device.close.assert_called_once_with()
        with self.assertRaises(EncoderClosedError):
            edge_input.read()

    def test_requires_initialization(self) -> None:
        edge_input = GPIOZeroDigitalEdgeInput(17)
        with self.assertRaises(EncoderNotInitializedError):
            edge_input.read()


if __name__ == "__main__":
    unittest.main()
