import unittest
from concurrent.futures import ThreadPoolExecutor

from robot_hat.exceptions import (
    EncoderBackendError,
    EncoderClosedError,
    EncoderNotInitializedError,
)
from robot_hat.mock.quadrature_counter import MockQuadratureCounterBackend


class TestMockQuadratureCounterBackend(unittest.TestCase):
    def test_zero_argument_lifecycle_and_idempotence(self) -> None:
        backend = MockQuadratureCounterBackend()

        with self.assertRaises(EncoderNotInitializedError):
            backend.read_snapshot()
        backend.initialize()
        backend.initialize()
        self.assertEqual(backend.read_snapshot().count, 0)
        backend.close()
        backend.close()
        with self.assertRaises(EncoderClosedError):
            backend.read_snapshot()

    def test_positive_negative_absolute_and_reset_counts(self) -> None:
        backend = MockQuadratureCounterBackend()
        backend.initialize()

        backend.advance(120)
        backend.advance(-20)
        self.assertEqual(backend.read_snapshot().count, 100)
        backend.set_count(-50)
        self.assertEqual(backend.read_snapshot().count, -50)
        backend.reset()
        self.assertEqual(backend.read_snapshot().count, 0)
        backend.reset(-7)
        self.assertEqual(backend.read_snapshot().count, -7)

    def test_invalid_diagnostics_and_injected_clock(self) -> None:
        backend = MockQuadratureCounterBackend(monotonic_ns=lambda: 1234)
        backend.initialize()

        backend.inject_invalid_transitions(3)
        snapshot = backend.read_snapshot()

        self.assertEqual(snapshot.timestamp_monotonic_ns, 1234)
        self.assertEqual(snapshot.invalid_transitions, 3)

    def test_availability_and_read_error_injection(self) -> None:
        backend = MockQuadratureCounterBackend()
        backend.initialize()

        backend.set_available(False)
        with self.assertRaises(EncoderBackendError):
            backend.read_snapshot()
        backend.set_available(True)
        backend.set_read_error(OSError("injected"))
        with self.assertRaises(OSError):
            backend.read_snapshot()
        backend.set_read_error(None)
        self.assertEqual(backend.read_snapshot().count, 0)

    def test_advances_are_atomic_between_threads(self) -> None:
        backend = MockQuadratureCounterBackend()
        backend.initialize()

        def advance_many() -> None:
            for _ in range(1000):
                backend.advance(1)

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(advance_many) for _ in range(4)]
            for future in futures:
                future.result()

        self.assertEqual(backend.read_snapshot().count, 4000)


if __name__ == "__main__":
    unittest.main()
